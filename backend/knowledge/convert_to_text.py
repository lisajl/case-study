import json

# Load the JSON data
with open('final_data.json', 'r') as file:
    knowledge_base = json.load(file)

# Function to convert each product part info into a structured text
def convert_to_text(knowledge_base):
    text_data = []
    for item in knowledge_base:
        part_name = item.get("part_name", "Unknown part")
        # appliance = item.get("appliance", "Unknown appliance")
        partselect_part_number = item.get("partselect_part_number", "Unknown part number")
        manufacturer_part_number = item.get("manufacturer_part_number", "Unknown manufacturer part number")
        manufacturer = item.get("manufacturer", "Unknown manufacturer")
        made_for = ", ".join(item.get("made_for", []))
        price = item.get("price", "Unknown price")
        description = item.get("description", "No description available")
        rating = item.get("rating", "No rating")
        num_reviews = item.get("num_reviews", "No reviews")
        troubleshooting = item.get("troubleshooting", "No troubleshooting available")
        compatible_models = ", ".join(item.get("compatible_models", []))

        # Construct text for each item
        text_data.append(f"Part Name: {part_name}\n"
                        #  f"Appliance: {appliance}\n"
                         f"PartSelect Part Number: {partselect_part_number}\n"
                         f"Manufacturer Part Number: {manufacturer_part_number}\n"
                         f"Manufacturer: {manufacturer}\n"
                         f"Made For: {made_for}\n"
                         f"Price: {price}\n"
                         f"Description: {description}\n"
                         f"Rating: {rating}\n"
                         f"Number of Reviews: {num_reviews}\n"
                         f"Troubleshooting: {troubleshooting}\n"
                         f"Compatible Models: {compatible_models}\n\n")
    
    return "\n".join(text_data)

# Convert the knowledge base to a structured text format
text_output = convert_to_text(knowledge_base)

# Optionally, save the structured text to a file for further processing
with open("knowledge_base.txt", "w") as text_file:
    text_file.write(text_output)
