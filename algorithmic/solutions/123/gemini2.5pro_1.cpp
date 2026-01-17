#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <vector>

// Global for convenience to avoid passing n everywhere.
// Using a boolean array for set membership tests is faster than std::set or binary search on a sorted vector.
int N_val;
std::vector<bool> s_map;

// Helper to print a query for a set S.
void print_query(const std::vector<int>& s) {
    if (s.empty()) {
        // According to the problem, S must be non-empty.
        // This case is handled by adding an element if S would be empty.
        // But as a safeguard:
        std::cout << "? 1 1" << std::endl;
        return;
    }
    std::cout << "? " << s.size();
    for (int x : s) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
}

// Helper to make a guess.
void make_guess(int g) {
    std::cout << "! " << g << std::endl;
}

// Partitions a set U into T (candidates if R was true) and F (candidates if R was false).
void form_tf(const std::vector<int>& U, const std::vector<int>& S, const std::string& R,
             std::vector<int>& T, std::vector<int>& F) {
    T.clear();
    F.clear();

    if (S.empty()) {
        if (R == "YES") { // x in empty set
            // F = U, T is empty
            F = U;
        } else { // x not in empty set
            // T = U, F is empty
            T = U;
        }
        return;
    }

    std::fill(s_map.begin(), s_map.end(), false);
    for (int x : S) {
        s_map[x] = true;
    }

    bool response_is_yes = (R == "YES");
    for (int x : U) {
        if (response_is_yes == s_map[x]) {
            T.push_back(x);
        } else {
            F.push_back(x);
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N_val;
    s_map.resize(N_val + 1);

    std::vector<int> U(N_val);
    std::iota(U.begin(), U.end(), 1);

    std::vector<int> S_prev;
    std::string R_prev;
    int guesses_left = 2;

    while (U.size() > guesses_left) {
        std::vector<int> S_curr;
        if (S_prev.empty()) {
            // First query: split current candidates in half.
            S_curr.reserve(U.size() / 2);
            for (size_t i = 0; i < U.size() / 2; ++i) {
                S_curr.push_back(U[i]);
            }
        } else {
            // Subsequent queries: optimal S splits both T_prev and F_prev in half.
            std::vector<int> T_prev, F_prev;
            form_tf(U, S_prev, R_prev, T_prev, F_prev);
            
            S_curr.reserve(T_prev.size() / 2 + F_prev.size() / 2);
            for (size_t i = 0; i < T_prev.size() / 2; ++i) {
                S_curr.push_back(T_prev[i]);
            }
            for (size_t i = 0; i < F_prev.size() / 2; ++i) {
                S_curr.push_back(F_prev[i]);
            }
        }
        
        // A query set must be non-empty.
        if (S_curr.empty() && !U.empty()) {
            S_curr.push_back(U[0]);
        }

        print_query(S_curr);
        std::string R_curr;
        std::cin >> R_curr;

        // Update candidate set U based on the last two answers.
        if (!S_prev.empty()) {
            std::vector<int> T_prev, F_prev;
            form_tf(U, S_prev, R_prev, T_prev, F_prev);
            
            std::vector<int> T_curr, F_curr;
            form_tf(U, S_curr, R_curr, T_curr, F_curr);
            
            std::vector<int> U_new = T_prev;
            
            std::fill(s_map.begin(), s_map.end(), false);
            for(int x : T_curr) s_map[x] = true;

            for (int x : F_prev) {
                if (s_map[x]) {
                    U_new.push_back(x);
                }
            }
            U = U_new;
        }

        S_prev = S_curr;
        R_prev = R_curr;

        // Speculative guess logic
        if (guesses_left > 0 && !U.empty()) {
            std::vector<int> T_hypo, F_hypo;
            form_tf(U, S_curr, R_curr, T_hypo, F_hypo);
            
            if (T_hypo.size() == 1) {
                int g = T_hypo[0];
                make_guess(g);
                guesses_left--;
                std::string judge_reply;
                std::cin >> judge_reply;

                if (judge_reply == ":)") {
                    return 0; // Correct guess, we are done.
                } else { // Incorrect guess, R_curr must have been a lie.
                    U = F_hypo;
                    
                    // The next answer must be true, so we can do a binary search.
                    std::vector<int> S_new;
                    S_new.reserve(U.size() / 2);
                    for(size_t i=0; i<U.size()/2; ++i) S_new.push_back(U[i]);

                    if (S_new.empty() && !U.empty()) S_new.push_back(U[0]);
                    
                    if (U.empty()) { // Should not happen with valid logic, but as a safeguard.
                        S_prev.clear();
                        continue;
                    }

                    print_query(S_new);
                    std::string R_new;
                    std::cin >> R_new;
                    
                    // Since R_new is true, we update U with perfect information.
                    std::vector<int> T_true, F_false;
                    form_tf(U, S_new, R_new, T_true, F_false);
                    U = T_true;
                    
                    // Set up for the next normal iteration.
                    S_prev = S_new;
                    R_prev = R_new;
                }
            }
        }
    }

    // Final guessing phase for the remaining candidates.
    for (int g : U) {
        make_guess(g);
        std::string judge_reply;
        std::cin >> judge_reply;
        if (judge_reply == ":)") {
            return 0;
        }
    }

    return 0;
}