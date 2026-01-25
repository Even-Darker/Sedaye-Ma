from src.utils.parsers import HandleParser

def test_parser():
    print("Testing HandleParser...")
    
    # Test 1: Simple list with @
    text1 = """
@user1
@user2
    """
    handles1 = HandleParser.extract_handles(text1)
    print(f"Test 1: {handles1} (Expected: ['user1', 'user2'])")
    
    # Test 2: Mixed text with Persian and numbers
    text2 = """
ترتیبشونو بدین با گزینه ای مثل میس اینفورمیشن. لطفا پخش کنید. یه نفری بی فایده س  
1.     @ziziuni
2.     @mahdisili
3.     @zinevesht
4.     @setareh_sadat_ghotbi 
    """
    handles2 = HandleParser.extract_handles(text2)
    print(f"Test 2: {handles2} (Expected: ['ziziuni', 'mahdisili', 'zinevesht', 'setareh_sadat_ghotbi'])")
    
    # Test 3: URLs
    text3 = "Check https://instagram.com/bad_page and instagram.com/another_one"
    handles3 = HandleParser.extract_handles(text3)
    print(f"Test 3: {handles3} (Expected: ['bad_page', 'another_one'])")
    
    # Test 4: Too long handle (should be REJECTED, not truncated)
    # 31 characters: aaaaaaaaaa bbbbbbbbbb cccccccccc d
    long_handle = "@iamlongerthanthirtycharacterssolong"
    text4 = f"This should be ignored: {long_handle}"
    handles4 = HandleParser.extract_handles(text4)
    print(f"Test 4: {handles4} (Expected: [])")
    
    # Test 5: The user's specific long handle (29 chars)
    valid_long = "@gsksbsakhsjsbaiavssksbskabsjs"
    text5 = f"Valid long handle: {valid_long}"
    handles5 = HandleParser.extract_handles(text5)
    print(f"Test 5: {handles5} (Expected: ['gsksbsakhsjsbaiavssksbskabsjs'])")

if __name__ == "__main__":
    test_parser()
