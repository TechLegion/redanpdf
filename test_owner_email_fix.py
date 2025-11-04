"""
Test script to verify that all Document() creations include owner_email parameter.
This is a code-level test that checks the actual source code.
"""

import os
import re

def check_document_creations_have_owner_email(file_path):
    """Check if Document() creations in a file include owner_email"""
    issues = []
    
    if not os.path.exists(file_path):
        return issues, 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find all Document( occurrences
    document_creations = []
    for i, line in enumerate(lines, 1):
        if 'Document(' in line and 'def ' not in line:
            # Get context (next 15 lines to see the full Document() call)
            context_start = max(0, i - 2)
            context_end = min(len(lines), i + 15)
            context = '\n'.join(lines[context_start:context_end])
            
            document_creations.append({
                'line': i,
                'line_content': line,
                'context': context
            })
    
    # Check each Document() creation
    for creation in document_creations:
        context = creation['context']
        
        # Check if it has owner_id (indicating it's a user-created document)
        if 'owner_id' in context and 'current_user' in context:
            # Check if owner_email is present
            if 'owner_email' not in context:
                # But exclude cases where it's copying from original_doc (those are handled differently)
                if 'original_doc.owner_email' not in context and 'doc.owner_email' not in context:
                    issues.append({
                        'file': file_path,
                        'line': creation['line'],
                        'issue': 'Document() creation with owner_id but missing owner_email',
                        'code': creation['line_content'].strip()
                    })
    
    return issues, len(document_creations)

def main():
    print("🧪 Testing Document Creation Fix - Checking Code for owner_email")
    print("=" * 70)
    
    files_to_check = [
        'pdf_saas_app/app/api/documents.py',
        'pdf_saas_app/app/api/pdf.py'
    ]
    
    all_issues = []
    total_creations = 0
    
    for file_path in files_to_check:
        print(f"\n📄 Checking {file_path}...")
        issues, creations = check_document_creations_have_owner_email(file_path)
        total_creations += creations
        
        if issues:
            print(f"   ⚠️  Found {len(issues)} potential issue(s):")
            for issue in issues:
                print(f"      Line {issue['line']}: {issue['issue']}")
                print(f"      Code: {issue['code']}")
                all_issues.append(issue)
        else:
            print(f"   ✅ All {creations} Document() creations look good!")
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"Files checked: {len(files_to_check)}")
    print(f"Total Document() creations found: {total_creations}")
    print(f"Issues found: {len(all_issues)}")
    
    if all_issues:
        print("\n❌ ISSUES DETECTED:")
        for issue in all_issues:
            print(f"\n   File: {issue['file']}")
            print(f"   Line: {issue['line']}")
            print(f"   Issue: {issue['issue']}")
            print(f"   Code: {issue['code']}")
        return False
    else:
        print("\n✅ All Document() creations properly include owner_email!")
        print("\n🎉 Code verification passed! All fixes are in place.")
        return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
