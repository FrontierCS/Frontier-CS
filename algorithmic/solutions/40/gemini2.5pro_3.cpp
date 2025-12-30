#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

// Function to perform a query and read the result
int ask_query(const std::vector<int>& indices) {
    if (indices.empty()) {
        return 0;
    }
    std::cout << "0 " << indices.size();
    for (int idx : indices) {
        std::cout << " " << idx;
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    // In an interactive problem, it's good practice to check for early termination signals
    if (result == -1) {
        exit(0);
    }
    return result;
}

// Function to submit the final answer
void give_answer(const std::string& s) {
    std::cout << "1 " << s << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::string s(n, ' ');

    // Step 1: Determine the first character, s[0] (using 1-based indexing for queries)
    std::vector<int> all_indices(n);
    std::iota(all_indices.begin(), all_indices.end(), 1);
    int f_all = ask_query(all_indices);

    std::vector<int> rem_indices;
    if (n > 1) {
        rem_indices.resize(n - 1);
        std::iota(rem_indices.begin(), rem_indices.end(), 2);
    }
    int f_rem = ask_query(rem_indices);

    if (f_all > f_rem) {
        s[0] = '(';
    } else {
        s[0] = ')';
    }

    // Step 2: Use s[0] as a reference to determine all other characters
    int p_ref = 1;
    char ref_char = s[0];

    for (int i = 2; i <= n; ++i) {
        int res;
        if (ref_char == '(') {
            // Query f(s_ref s_i)
            res = ask_query({p_ref, i});
            if (res == 1) {
                s[i - 1] = ')';
            } else {
                s[i - 1] = '(';
            }
        } else { // ref_char == ')'
            // Query f(s_i s_ref)
            res = ask_query({i, p_ref});
            if (res == 1) {
                s[i - 1] = '(';
            } else {
                s[i - 1] = ')';
            }
        }
    }

    give_answer(s);

    return 0;
}