#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <iterator>

int main() {
    // Standard setup for fast I/O in C++ competitive programming.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int m;
    std::cin >> m;

    // count_l_to_r[k] stores the number of times we have taken passage k
    // while flipping a chamber's mark from "left" to "right".
    std::vector<int> count_l_to_r(m, 0);
    
    // count_r_to_l[k] is analogous for "right" to "left" flips.
    std::vector<int> count_r_to_l(m, 0);

    while (true) {
        std::string stone_location;
        std::cin >> stone_location;

        if (stone_location == "treasure") {
            // The goal is reached, terminate the program.
            break;
        }

        if (stone_location == "center") {
            // A new chamber is discovered. We mark it with "left" and take passage 0.
            // This sets a reference passage for this chamber and explores one passage.
            std::cout << "0 left 0" << std::endl;
        } else if (stone_location == "left") {
            // The chamber is marked "left". To explore a new passage, we flip its mark
            // to "right". We choose the passage k that has been used least often for this
            // type of flip to ensure all passages are eventually chosen.
            auto min_it = std::min_element(count_l_to_r.begin(), count_l_to_r.end());
            int best_k = std::distance(count_l_to_r.begin(), min_it);
            
            // The action "0 right k" keeps the reference passage the same (d=0),
            // flips the mark to "right", and takes passage k.
            std::cout << "0 right " << best_k << std::endl;
            count_l_to_r[best_k]++;
        } else if (stone_location == "right") {
            // This is the symmetric case for a chamber marked "right". We flip it
            // back to "left" and explore the least-used passage for this flip type.
            auto min_it = std::min_element(count_r_to_l.begin(), count_r_to_l.end());
            int best_k = std::distance(count_r_to_l.begin(), min_it);
            
            std::cout << "0 left " << best_k << std::endl;
            count_r_to_l[best_k]++;
        }
    }
    
    return 0;
}