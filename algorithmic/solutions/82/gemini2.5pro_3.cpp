#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to perform a query
int ask(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) {
        // Exit immediately if the judge returns -1
        exit(0);
    }
    return result;
}

// Function to print the final answer
void answer(const std::vector<int>& p) {
    std::cout << "!";
    for (size_t i = 0; i < p.size(); ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p(n);
    int zero_idx = -1;

    // Find the index of the element 0
    // If p_i = 0, then for any j, k != i, (p_i | p_j) | (p_i | p_k) = p_j | p_k.
    // The latter is the result of query(j, k).
    // This property uniquely identifies the index of 0.
    // We can test each index i. For each i, we pick two other indices j and k
    // and check if the condition holds. With n >= 3, we can always find such j, k.
    
    // To do this efficiently, we can maintain a candidate for the zero index
    // and verify it against other indices.
    int cand_z = 1;
    for (int i = 2; i <= n; ++i) {
        int or_cand_i = ask(cand_z, i);
        
        int other_idx = (cand_z == 1 && i == 2) ? 3 : (cand_z == 1 ? 2 : 1);
        if (other_idx > n) other_idx = (cand_z == 2) ? 3: 2; // for n=3 case

        int or_cand_other = ask(cand_z, other_idx);
        int or_i_other = ask(i, other_idx);

        // Test if cand_z could be 0
        if ((or_cand_i | or_cand_other) == or_i_other) {
            // cand_z is a possibility. Keep it.
        } 
        // Test if i could be 0
        else if ((or_cand_i | or_i_other) == or_cand_other) {
            cand_z = i;
        } 
        // Test if other_idx could be 0
        else if ((or_cand_other | or_i_other) == or_cand_i) {
            cand_z = other_idx;
        }
    }
    zero_idx = cand_z;
    
    // Now that we have the index of 0, we can determine the entire permutation
    p[zero_idx - 1] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) {
            continue;
        }
        p[i - 1] = ask(zero_idx, i);
    }

    answer(p);

    return 0;
}