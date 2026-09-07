import csv


modes = ["Ignore unsures", "Mark unsures as valid"]


comparisions = ["Simon"]
systems = ["#3", "#4", "#5", "#6", "#7", "#8", "#9", "#12"]




previous_sets = [[], [], [], []]


for mode in modes:
  
   print(f"\n\nMode: {mode}")


   for file in comparisions:
       valid = []
       invalid = []


       with open(f"Testing/5.1/DBpedia triples human annotations - {file}-Random 50_10.csv", 'r', encoding='utf-8') as current_file:
           reader = csv.reader(current_file)
           next(reader)  # Skip the header row
           for line in reader:
               triple = [line[1], line[2], line[3]]
               if mode == "Ignore unsures":
                   if line[4] == "Valid":
                       valid.append(triple)
                   elif line[4] == "Invalid":
                       invalid.append(triple)
               elif mode == "Mark unsures as valid":
                   if line[4] == "Invalid":
                       invalid.append(triple)
                   elif line[4] == "Valid" or line[4] == r"Unsure ¯\_(ツ)_/¯":
                       valid.append(triple)
               elif mode == "Mark unsures as invalid":
                   if line[4] == "Valid":
                       valid.append(triple)
                   elif line[4] == "Invalid" or line[4] == r"Unsure ¯\_(ツ)_/¯":
                       invalid.append(triple)
       print(f"len(valid): {len(valid)}")
       print(f"len(invalid): {len(invalid)}")


       for system in systems:
           tps = []
           fps = []
           tns = []
           fns = []
          
           marked_as_valid_triples = []
           true_positive = 0
           false_positive = 0
          
           with open(f"Testing/5.1/random_wikipedia_articles-{system}.csv", 'r', encoding='utf-8') as current_system:
               reader = csv.reader(current_system)
               for line in reader:
                   marked_as_valid_triple = [line[0], line[1], line[2]]
                   marked_as_valid_triples.append(marked_as_valid_triple)
                   #print(marked_as_valid_triple)


                   if marked_as_valid_triple in valid:
                       #print("True Positive")
                       true_positive += 1
                       tps.append(marked_as_valid_triple)
      
                   elif marked_as_valid_triple in invalid:
                       #print("False Positive")
                       false_positive += 1
                       fps.append(marked_as_valid_triple)
                  
                   else:
                       if mode != "Ignore unsures":
                           print(f"Triple not found in valid or invalid: {marked_as_valid_triple}")


           print(f"System {system} results for file {file}:")
           print(f"True Positives: {true_positive}")               
           print(f"False Positives: {false_positive}")
           for triple in invalid:
               if triple not in marked_as_valid_triples:
                   tns.append(triple)
          
           for triple in valid:
               if triple not in marked_as_valid_triples:
                   fns.append(triple)
          
           print(f"True Negatives: {len(tns)}")
           print(f"False Negatives: {len(fns)}")
            

           total = true_positive + false_positive + (len(invalid) - false_positive) + (len(valid) - true_positive)


           precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) > 0 else 0
           recall = true_positive / (len(valid)) if (len(valid)) > 0 else 0


           f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0


           print(f"Precision: {precision:.4f}")
           print(f"Recall: {recall:.4f}")
           print(f"F1 Score: {f1_score:.4f}")
           print(f"Total: {total}")
           print("-----------------------------")


           if mode == "Ignore unsures":
               previous_sets = [tps, fps, tns, fns]

