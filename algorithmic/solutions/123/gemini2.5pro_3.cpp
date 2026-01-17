#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <unordered_set>

void ask_query(const std::vector<int>& s) {
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

    std::vector<int> p(n);
    std::iota(p.begin(), p.end(), 1);
    std::vector<int> l;

    if (n > 2) {
        std::vector<int> s;
        for (size_t i = 0; i < p.size() / 2; ++i) {
            s.push_back(p[i]);
        }
        ask_query(s);
        std::string ans;
        std::cin >> ans;

        std::unordered_set<int> s_set(s.begin(), s.end());
        bool ans_is_yes = (ans == "YES");

        std::vector<int> l_new;
        for (int x : p) {
            bool x_in_s = s_set.count(x);
            bool u_contains_x = (ans_is_yes == x_in_s);
            if (!u_contains_x) {
                l_new.push_back(x);
            }
        }
        l = l_new;
    }

    while (p.size() > 2) {
        std::unordered_set<int> l_set(l.begin(), l.end());
        std::vector<int> q;
        for (int x : p) {
            if (l_set.find(x) == l_set.end()) {
                q.push_back(x);
            }
        }

        std::vector<int> s;
        for (size_t i = 0; i < l.size() / 2; ++i) {
            s.push_back(l[i]);
        }
        for (size_t i = 0; i < q.size() / 2; ++i) {
            s.push_back(q[i]);
        }
        
        if (s.empty()) {
            if (!p.empty()) {
                s.push_back(p[0]);
            } else {
                break;
            }
        }

        ask_query(s);
        std::string ans;
        std::cin >> ans;

        std::unordered_set<int> s_set(s.begin(), s.end());
        bool ans_is_yes = (ans == "YES");

        std::vector<int> p_new;
        std::vector<int> l_new;

        for (int x : p) {
            bool x_in_s = s_set.count(x);
            bool u_contains_x = (ans_is_yes == x_in_s);
            bool l_contains_x = l_set.count(x);

            if (!(l_contains_x && !u_contains_x)) {
                p_new.push_back(x);
                if (!u_contains_x) {
                    l_new.push_back(x);
                }
            }
        }
        p = p_new;
        l = l_new;
    }

    for (int candidate : p) {
        make_guess(candidate);
        std::string res;
        std::cin >> res;
        if (res == ":)") {
            return 0;
        }
    }

    return 0;
}