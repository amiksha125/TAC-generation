from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import re
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

temp_count = 0
next_quad = 0
code = []

def new_temp():
    global temp_count
    temp_count += 1
    return f"t{temp_count}"

def gen(code_line):
    global next_quad
    if code_line.strip():
        code.append(f"{next_quad}: {code_line}")
        next_quad += 1

def backpatch(list_to_patch, label):
    for i in list_to_patch:
        if i < len(code):
            code[i] = code[i].replace("____", str(label))

def makelist(index):
    return [index]

def parse_expression(expression):
    match = re.match(r"(\w+)\s*([\+\-\*/])\s*(\w+)", expression.strip())
    return match.groups() if match else None

def generate_statement(line):
    line = line.strip()
    if " = " in line:
        left, right_expr = line.split(" = ")
        parsed = parse_expression(right_expr)
        if parsed:
            operand1, operator, operand2 = parsed
            t = new_temp()
            gen(f"{t} = {operand1} {operator} {operand2}")
            gen(f"{left} = {t}")
        else:
            gen(line) 
    else:
        gen(line)

def generate_while_loop(condition, body):
    global next_quad
    M1_quad = next_quad
    gen(f"if {condition} goto ____") 
    E_true = makelist(next_quad - 1)
    E_false = makelist(next_quad)
    gen("goto ____")

    M2_quad = next_quad
    generate_body(body)

    gen(f"goto {M1_quad}") # for jumping to while condition9/=[]
    backpatch(E_true, M2_quad)
    backpatch(E_false, next_quad)

def generate_for_loop(init, condition, increment, body):
    global next_quad
    gen(init) 
    M1_quad = next_quad
    gen(f"if {condition} goto ____")
    E_true = makelist(next_quad - 1)
    E_false = makelist(next_quad)
    gen("goto ____")

    M2_quad = next_quad
    generate_body(body)

    gen(increment)  # Increment step
    gen(f"goto {M1_quad}")  # Jump back to loop condition
    backpatch(E_true, M2_quad)
    backpatch(E_false, next_quad)

def generate_if_else(condition, true_body, false_body):
    global next_quad
    gen(f"if {condition} goto ____")
    E_true = makelist(next_quad - 1)
    E_false = makelist(next_quad)
    gen("goto ____")

    M1_quad = next_quad
    generate_body(true_body)

    M2_quad = next_quad
    gen("goto ____") 
    E_next = makelist(next_quad - 1)

    M3_quad = next_quad
    generate_body(false_body)
    
    backpatch(E_true, M1_quad)
    backpatch(E_false, M3_quad)
    backpatch(E_next, next_quad)

def generate_body(body):
    global next_quad
    nested_code = "\n".join(body).strip()

    if "if" in nested_code and "else" in nested_code:
        match = re.search(r"if\s*\(([^)]+)\)\s*\{(.*?)\}\s*else\s*\{(.*?)\}", nested_code, re.DOTALL)
        if match:
            return generate_if_else(match.group(1), match.group(2).split("\n"), match.group(3).split("\n"))

    elif "while" in nested_code:
        match = re.search(r"while\s*\(([^)]+)\)\s*\{(.*?)\}", nested_code, re.DOTALL)
        if match:
            return generate_while_loop(match.group(1), match.group(2).split("\n"))

    elif "for" in nested_code:
        match = re.search(r"for\s*\(([^)]+)\)\s*\{(.*?)\}", nested_code, re.DOTALL)
        if match:
            parts = [p.strip() for p in match.group(1).split(";")]
            if len(parts) == 3:
                return generate_for_loop(parts[0], parts[1], parts[2], match.group(2).split("\n"))

    # If not a control structure, treat it as a sequence of statements
    for line in body:
        generate_statement(line)

def parse_code(code_text):
    code_text = code_text.strip()
    
    if "for" in code_text:
        match = re.search(r"for\s*\(([^)]+)\)\s*\{(.*?)\}", code_text, re.DOTALL)
        if match:
            parts = [p.strip() for p in match.group(1).split(";")]
            if len(parts) == 3:
                return generate_for_loop(parts[0], parts[1], parts[2], match.group(2).split("\n"))

    elif "while" in code_text:
        match = re.search(r"while\s*\(([^)]+)\)\s*\{(.*?)\}", code_text, re.DOTALL)
        if match:
            return generate_while_loop(match.group(1), match.group(2).split("\n"))

    elif "if" in code_text and "else" in code_text:
        match = re.search(r"if\s*\(([^)]+)\)\s*\{(.*?)\}\s*else\s*\{(.*?)\}", code_text, re.DOTALL)
        if match:
            return generate_if_else(match.group(1), match.group(2).split("\n"), match.group(3).split("\n"))

    # If no loops or conditions, treat as simple code block
    return generate_body(code_text.split("\n"))

@app.post("/generate_tac/")
async def generate_tac(file: UploadFile = File(...)):
    global code, next_quad
    code = []
    next_quad = 0

    content = await file.read()
    code_text = content.decode("utf-8")
    parse_code(code_text)

    return {"tac": code}