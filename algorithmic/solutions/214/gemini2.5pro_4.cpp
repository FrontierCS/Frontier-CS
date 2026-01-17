#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int n;
std::vector<int> a;
std::vector<int> pos;
std::vector<std::pair<int, int>> operations;

void apply_reverse_op(int l, int r) {
    operations.push_back({l, r});
    int l_ptr = l, r_ptr = r;
    while (l_ptr < r_ptr) {
        int val1 = a[l_ptr];
        int val2 = a[r_ptr];
        std::swap(a[l_ptr], a[r_ptr]);
        pos[val1] = r_ptr;
        pos[val2] = l_ptr;
        l_ptr++;
        r_ptr--;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    std::cin >> n;
    a.resize(n + 1);
    pos.resize(n + 1);
    for (int i = 1; i <= n; ++i) {
        std::cin >> a[i];
        pos[a[i]] = i;
    }

    int x = 3;

    for (int i = 1; i <= n; ++i) {
        while (pos[i] - i >= 3) {
            int current_pos = pos[i];
            apply_reverse_op(current_pos - 3, current_pos);
        }

        if (pos[i] - i == 2) {
            apply_reverse_op(i + 1, i + 2);
            apply_reverse_op(i, i + 1);
        }

        if (pos[i] - i == 1) {
            apply_reverse_op(i, i + 1);
        }
    }
    
    std::cout << x << "\n";
    std::cout << operations.size() << "\n";
    for (const auto& op : operations) {
        std::cout << op.first << " " << op.second << "\n";
    }

    return 0;
}