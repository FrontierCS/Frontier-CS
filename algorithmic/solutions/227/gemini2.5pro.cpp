#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

void solve() {
    int n;
    std::cin >> n;
    std::vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> p[i];
    }

    std::vector<int> a, b, c, d;
    int last_a = 0;
    int last_c = 0;
    int last_b = n + 1;
    int last_d = n + 1;

    for (int x : p) {
        bool can_a = (x > last_a);
        bool can_c = (x > last_c);
        
        int is_cand_type = 0;
        int max_l = -1;

        if (can_a) {
            max_l = last_a;
            is_cand_type = 1;
        }
        if (can_c && last_c > max_l) {
            max_l = last_c;
            is_cand_type = 2;
        }

        bool can_b = (x < last_b);
        bool can_d = (x < last_d);
        
        int ds_cand_type = 0;
        int min_l = n + 2;
        
        if (can_b) {
            min_l = last_b;
            ds_cand_type = 1;
        }
        if (can_d && last_d < min_l) {
            min_l = last_d;
            ds_cand_type = 2;
        }

        if (is_cand_type != 0 && ds_cand_type != 0) {
            if (x - max_l <= min_l - x) {
                if (is_cand_type == 1) {
                    a.push_back(x);
                    last_a = x;
                } else {
                    c.push_back(x);
                    last_c = x;
                }
            } else {
                if (ds_cand_type == 1) {
                    b.push_back(x);
                    last_b = x;
                } else {
                    d.push_back(x);
                    last_d = x;
                }
            }
        } else if (is_cand_type != 0) {
            if (is_cand_type == 1) {
                a.push_back(x);
                last_a = x;
            } else {
                c.push_back(x);
                last_c = x;
            }
        } else {
            if (ds_cand_type == 1) {
                b.push_back(x);
                last_b = x;
            } else {
                d.push_back(x);
                last_d = x;
            }
        }
    }

    std::cout << a.size() << " " << b.size() << " " << c.size() << " " << d.size() << "\n";

    for (size_t i = 0; i < a.size(); ++i) {
        std::cout << a[i] << (i == a.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    for (size_t i = 0; i < b.size(); ++i) {
        std::cout << b[i] << (i == b.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    for (size_t i = 0; i < c.size(); ++i) {
        std::cout << c[i] << (i == c.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    for (size_t i = 0; i < d.size(); ++i) {
        std::cout << d[i] << (i == d.size() - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}