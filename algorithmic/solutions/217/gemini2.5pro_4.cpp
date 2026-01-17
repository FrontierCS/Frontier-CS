#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <random>
#include <chrono>

using namespace std;

int N, M;

int ask(const vector<int>& q_indices) {
    if (q_indices.empty()) {
        return 0;
    }
    cout << "? " << q_indices.size();
    for (int idx : q_indices) {
        cout << " " << idx;
    }
    cout << endl;
    int result;
    cin >> result;
    return result;
}

void answer(const vector<int>& stick) {
    cout << "!";
    for (int idx : stick) {
        cout << " " << idx;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M;

    if (M == 1) {
        vector<int> stick(N);
        iota(stick.begin(), stick.end(), 1);
        answer(stick);
        return 0;
    }

    set<int> all_dangos_set;
    for (int i = 1; i <= N * M; ++i) {
        all_dangos_set.insert(i);
    }

    set<int> used_dangos;

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    for (int i = 1; i <= M; ++i) {
        vector<int> current_stick;
        set<int> current_stick_set;

        vector<int> available_dangos;
        for (int dango : all_dangos_set) {
            if (used_dangos.find(dango) == used_dangos.end()) {
                available_dangos.push_back(dango);
            }
        }
        
        current_stick.push_back(available_dangos[0]);
        current_stick_set.insert(available_dangos[0]);
        
        for (int k = 2; k <= N; ++k) {
            vector<int> candidates;
            for(int d : available_dangos) {
                if (current_stick_set.find(d) == current_stick_set.end()) {
                    candidates.push_back(d);
                }
            }
            shuffle(candidates.begin(), candidates.end(), rng);

            for(int d_cand : candidates) {
                set<int> query_set;
                for (int d : available_dangos) {
                    query_set.insert(d);
                }
                for(int d_s : current_stick) {
                    query_set.erase(d_s);
                }
                query_set.erase(d_cand);
                
                vector<int> query_set_vec(query_set.begin(), query_set.end());
                
                if (ask(query_set_vec) == M - i + 1) { // Q(P) = M-i+1, check Q(P - {d}) == M-i+1
                    current_stick.push_back(d_cand);
                    current_stick_set.insert(d_cand);
                    break;
                }
            }
        }
        
        // My logic in explanation was slightly off. Q(U_current) = M-i+1. S size k. P = U_current \ S.
        // Q(P) = M-i.
        // A d in P is good if Q(P \ {d}) == M-i. bad if Q(P \ {d}) == M-i-1.
        // P \ {d} is U_current \ (S U {d}). So my check should be `== M-i`.
        // The first dango picked reduces available to M-i+1 of N-1 colors and M-i of 1 color.
        // A simpler invariant: let U be the set of ALL unused dangos. Initially all N*M.
        // After finding i-1 sticks, Q(U) = M-i+1.
        // To build stick i: S is partial stick.
        // good d means Q(U \ (S U {d})) == M-i.
        // U is `available_dangos` in my code.
        // So Q(available_dangos \ (current_stick U {d_cand})) should be M-i
        // My code's logic is `M-i+1`. Let me re-verify.
        // Let's analyze my code logic:
        // Q(available_dangos \ (current_stick U {d_cand})).
        // `available_dangos` is `U_current`. Size `N(M-i+1)`. Q on it is `M-i+1`.
        // `current_stick` size `k-1`. Let's say it's good.
        // Test `d_cand`. If good, `current_stick U {d_cand}` has `k` distinct colors.
        // After removing these `k` dangos, `k` colors will have count `M-i`, others `M-i+1`. Min is `M-i`.
        // If bad, `current_stick U {d_cand}` has `k` items, `k-1` distinct colors.
        // After removing, one color has count `M-i-1`. Min is `M-i-1`.
        // So `ask(query_set_vec) == M-i` is the correct check. I'll correct the code.
        // The first dango choice is arbitrary, no query needed.
        
        sort(current_stick.begin(), current_stick.end());
        answer(current_stick);
        
        for (int dango : current_stick) {
            used_dangos.insert(dango);
        }
    }
}


// Corrected logic implementation:
#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <random>
#include <chrono>

void corrected_main() {
    int N, M;
    std::cin >> N >> M;

    auto ask = [](const std::vector<int>& q_indices) {
        if (q_indices.empty()) {
            return 0;
        }
        std::cout << "? " << q_indices.size();
        for (int idx : q_indices) {
            std::cout << " " << idx;
        }
        std::cout << std::endl;
        int result;
        std::cin >> result;
        return result;
    };

    auto answer = [](const std::vector<int>& stick) {
        std::cout << "!";
        for (int idx : stick) {
            std::cout << " " << idx;
        }
        std::cout << std::endl;
    };


    if (M == 1) {
        std::vector<int> stick(N);
        std::iota(stick.begin(), stick.end(), 1);
        answer(stick);
        return;
    }

    std::set<int> used_dangos;
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    for (int i = 1; i <= M; ++i) {
        std::vector<int> current_stick;
        std::set<int> current_stick_set;

        std::vector<int> available_dangos;
        for (int j = 1; j <= N * M; ++j) {
            if (used_dangos.find(j) == used_dangos.end()) {
                available_dangos.push_back(j);
            }
        }
        
        // Find first dango for the stick. Any dango is fine.
        int first_dango = -1;
        for(int d : available_dangos) {
            first_dango = d;
            break;
        }
        current_stick.push_back(first_dango);
        current_stick_set.insert(first_dango);

        for (int k = 2; k <= N; ++k) {
            std::vector<int> candidates;
            for(int d : available_dangos) {
                if (current_stick_set.find(d) == current_stick_set.end()) {
                    candidates.push_back(d);
                }
            }
            std::shuffle(candidates.begin(), candidates.end(), rng);

            for(int d_cand : candidates) {
                std::vector<int> query_vec;
                for (int d : available_dangos) {
                    if (current_stick_set.find(d) == current_stick_set.end() && d != d_cand) {
                        query_vec.push_back(d);
                    }
                }
                
                if (ask(query_vec) == M - i) {
                    current_stick.push_back(d_cand);
                    current_stick_set.insert(d_cand);
                    break;
                }
            }
        }
        
        answer(current_stick);
        
        for (int dango : current_stick) {
            used_dangos.insert(dango);
        }
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    corrected_main();
    return 0;
}