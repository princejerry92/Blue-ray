import os
from docx import Document

def extract_text_from_file(file_path):
    """Extract text from a given file (txt or docx)."""
    if not os.path.isfile(file_path):
        raise ValueError("The provided path is not a valid file.")

    file_extension = file_path.rsplit('.', 1)[-1].lower()

    if file_extension == 'txt':
        return extract_text_from_txt(file_path)
    elif file_extension == 'docx':
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file type. Please provide a .txt or .docx file.")

def extract_text_from_txt(file_path):
    """Extract text from a .txt file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except Exception as e:
        raise Exception(f"Error reading .txt file: {str(e)}")

def extract_text_from_docx(file_path):
    """Extract text from a .docx file."""
    try:
        document = Document(file_path)
        text = []
        for para in document.paragraphs:
            text.append(para.text)
        return '\n'.join(text)
    except Exception as e:
        raise Exception(f"Error reading .docx file: {str(e)}")

if __name__ == "__main__":
    # Input file path from the user
    file_path = input("Enter the path to the file (txt or docx): ")
    
    try:
        extracted_text = extract_text_from_file(file_path)
        print("Extracted Text:")
        print(extracted_text)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
