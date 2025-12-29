#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int n;
std::vector<int> p;
std::vector<int> pos;
std::vector<std::pair<int, int>> ops;

void apply_op(int x, int y) {
    if (x <= 0 || y <= 0 || x + y >= n) {
        return; 
    }
    ops.push_back({x, y});

    std::vector<int> temp_p;
    temp_p.reserve(n);

    for (int i = n - y; i < n; ++i) temp_p.push_back(p[i]);
    for (int i = x; i < n - y; ++i) temp_p.push_back(p[i]);
    for (int i = 0; i < x; ++i) temp_p.push_back(p[i]);
    
    p = temp_p;

    for (int i = 0; i < n; ++i) {
        pos[p[i]] = i;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;
    p.resize(n);
    pos.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        std::cin >> p[i];
        pos[p[i]] = i;
    }

    if (n == 3 && p[1] != 2) {
        if (p[0] > p[2]) {
            apply_op(1, 1);
        }
    } else {
        for (int i = 1; i <= n; ++i) {
            int current_pos = pos[i];
            int target_pos = i - 1;

            if (current_pos == target_pos) {
                continue;
            }

            if (current_pos != n - 1) {
                if (current_pos < n - 2) {
                    apply_op(current_pos + 1, 1);
                } else { // current_pos == n - 2
                    apply_op(1, 2);
                    apply_op(1, 1);
                }
            }

            if (target_pos == n - 1) {
                continue;
            }
            
            if (target_pos < n-2) {
                 apply_op(1, target_pos + 1);
            } else { // target_pos == n-2
                apply_op(1, 1);
                apply_op(1, 2);
            }
        }
    }

    std::cout << ops.size() << "\n";
    for (const auto& op : ops) {
        std::cout << op.first << " " << op.second << "\n";
    }

    return 0;
}