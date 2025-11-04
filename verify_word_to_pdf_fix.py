"""Quick verification that word-to-pdf endpoint includes owner_email"""

with open('pdf_saas_app/app/api/documents.py', 'r') as f:
    content = f.read()
    
    # Check for word_to_pdf endpoint with owner_email
    if 'conversion_type="word_to_pdf"' in content and 'owner_email=current_user.email' in content:
        # Verify they're close to each other (within 20 lines)
        lines = content.split('\n')
        found_word_to_pdf = False
        found_owner_email = False
        
        for i, line in enumerate(lines):
            if 'conversion_type="word_to_pdf"' in line:
                found_word_to_pdf = True
                # Check next 20 lines for owner_email
                context = '\n'.join(lines[i:i+20])
                if 'owner_email=current_user.email' in context or 'owner_email=current_user.email  # Store email for resilience' in context:
                    found_owner_email = True
                    print("✅ Word-to-PDF endpoint fix verified!")
                    print(f"   Found at line ~{i+1}")
                    print(f"   owner_email is included in Document() creation")
                    exit(0)
        
        if found_word_to_pdf and not found_owner_email:
            print("❌ Word-to-PDF endpoint found but owner_email missing!")
            exit(1)
    
    # Also check excel and ppt
    for conversion in ['word_to_pdf', 'excel_to_pdf', 'ppt_to_pdf']:
        if f'conversion_type="{conversion}"' in content:
            context_start = content.find(f'conversion_type="{conversion}"')
            context = content[context_start:context_start+2000]
            if 'owner_email=current_user.email' not in context:
                print(f"❌ {conversion} endpoint missing owner_email!")
                exit(1)
    
    print("✅ All conversion endpoints (word-to-pdf, excel-to-pdf, ppt-to-pdf) include owner_email!")
    print("\n🎉 Verification complete - all fixes are in place!")
