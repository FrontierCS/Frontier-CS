#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

void ask_query(const std::vector<int>& s) {
    if (s.empty()) {
        // As a fallback for an empty query set, query a single arbitrary element.
        // This can happen if p_set and l_set become small.
        std::cout << "? 1 1" << std::endl;
        return;
    }
    std::cout << "? " << s.size();
    for (int x : s) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
}

void make_guess(int g) {
    std::cout << "! " << g << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p_set(n);
    std::iota(p_set.begin(), p_set.end(), 1);
    std::vector<int> l_set;

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    while (p_set.size() + l_set.size() > 2) {
        std::shuffle(p_set.begin(), p_set.end(), rng);
        std::shuffle(l_set.begin(), l_set.end(), rng);

        size_t p_ask_cnt = p_set.size() / 2;
        size_t l_ask_cnt = l_set.size() / 2;
        
        std::vector<int> s;
        s.reserve(p_ask_cnt + l_ask_cnt);
        for (size_t i = 0; i < p_ask_cnt; ++i) {
            s.push_back(p_set[i]);
        }
        for (size_t i = 0; i < l_ask_cnt; ++i) {
            s.push_back(l_set[i]);
        }
        
        if (s.empty()) {
            std::vector<int> all_candidates;
            all_candidates.insert(all_candidates.end(), p_set.begin(), p_set.end());
            all_candidates.insert(all_candidates.end(), l_set.begin(), l_set.end());
            if (!all_candidates.empty()) {
                s.push_back(all_candidates[0]);
            }
        }

        ask_query(s);
        std::string response;
        std::cin >> response;

        std::vector<bool> in_s(n + 1, false);
        for (int x : s) {
            in_s[x] = true;
        }

        std::vector<int> new_p_set;
        std::vector<int> new_l_set;

        if (response == "YES") {
            for (int x : p_set) {
                if (in_s[x]) new_p_set.push_back(x);
                else new_l_set.push_back(x);
            }
            for (int x : l_set) {
                if (in_s[x]) new_p_set.push_back(x);
            }
        } else { // NO
            for (int x : p_set) {
                if (!in_s[x]) new_p_set.push_back(x);
                else new_l_set.push_back(x);
            }
            for (int x : l_set) {
                if (!in_s[x]) new_p_set.push_back(x);
            }
        }
        
        p_set = new_p_set;
        l_set = new_l_set;
    }

    std::vector<int> final_candidates;
    final_candidates.insert(final_candidates.end(), p_set.begin(), p_set.end());
    final_candidates.insert(final_candidates.end(), l_set.begin(), l_set.end());
    
    std::sort(final_candidates.begin(), final_candidates.end());
    final_candidates.erase(std::unique(final_candidates.begin(), final_candidates.end()), final_candidates.end());

    for (int candidate : final_candidates) {
        make_guess(candidate);
        std::string response;
        std::cin >> response;
        if (response == ":)") {
            return 0;
        }
    }

    return 0;
}