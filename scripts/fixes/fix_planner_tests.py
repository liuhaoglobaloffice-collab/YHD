import re
from pathlib import Path

def fix_planner_tests(file_path):
    """Fix test_planner.py to use TaskDecomposition.tasks attribute"""
    content = Path(file_path).read_text(encoding='utf-8')
    
    # Pattern 1: tasks = planner.create_plan(parsed)
    # Add: task_list = tasks.tasks after it
    
    # Replace direct access to tasks with decomposition pattern
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # When we see "tasks = planner.create_plan"
        if re.search(r'tasks\s*=\s*planner\.create_plan\(', line):
            new_lines.append(line)
            # Add extraction line
            indent = len(line) - len(line.lstrip())
            new_lines.append(' ' * indent + 'task_list = tasks.tasks  # Extract task list from TaskDecomposition')
            
            # Now replace subsequent uses of 'tasks' with 'task_list' until next function
            i += 1
            while i < len(lines):
                next_line = lines[i]
                
                # Stop at next function definition
                if re.match(r'^\s*def\s+', next_line):
                    new_lines.append(next_line)
                    break
                    
                # Replace 'len(tasks)' with 'len(task_list)'
                next_line = re.sub(r'\blen\(tasks\)', 'len(task_list)', next_line)
                
                # Replace 'for task in tasks:' with 'for task in task_list:'
                next_line = re.sub(r'for\s+task\s+in\s+tasks:', 'for task in task_list:', next_line)
                
                # Replace standalone 'tasks' references (but not 'tasks.something')
                # This is tricky - only replace when it's not followed by a dot
                next_line = re.sub(r'\btasks\b(?!\.)', 'task_list', next_line)
                
                new_lines.append(next_line)
                i += 1
        else:
            new_lines.append(line)
            i += 1
    
    new_content = '\n'.join(new_lines)
    
    if new_content != content:
        Path(file_path).write_text(new_content, encoding='utf-8', newline='\n')
        return True
    return False

if __name__ == '__main__':
    file = 'tests/test_ai_brain/test_planner.py'
    if fix_planner_tests(file):
        print(f'Fixed {file}')
    else:
        print(f'No changes needed for {file}')
