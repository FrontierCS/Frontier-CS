#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <tuple>

// Using 1-based indexing for arrays to match problem statement
std::vector<int> val;
std::vector<int> pos;
int n;
std::vector<std::tuple<int, int, int>> operations;

void left_shift(int l, int r) {
    int first_val = val[l];
    for (int i = l; i < r; ++i) {
        val[i] = val[i + 1];
        pos[val[i]] = i;
    }
    val[r] = first_val;
    pos[first_val] = r;
}

void right_shift(int l, int r) {
    int last_val = val[r];
    for (int i = r; i > l; --i) {
        val[i] = val[i - 1];
        pos[val[i]] = i;
    }
    val[l] = last_val;
    pos[last_val] = l;
}

void apply_op(int l, int r, int dir) {
    operations.emplace_back(l, r, dir);
    if (dir == 0) {
        left_shift(l, r);
    } else {
        right_shift(l, r);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;
    val.resize(n + 1);
    pos.resize(n + 1);
    for (int i = 1; i <= n; ++i) {
        std::cin >> val[i];
        pos[val[i]] = i;
    }

    if (n == 1) {
        std::cout << "1 0\n";
        return 0;
    }

    int x = static_cast<int>(sqrt(n / 2.0) + 1.0);
    if (x % 2 != 0) {
        x++;
    }
    if (x > n) {
        x = n;
    }
    if (x % 2 != 0) {
        x--;
    }
    if (x < 2) {
        x = 2;
    }

    for (int i = 1; i <= n; ++i) {
        if (pos[i] == i) {
            continue;
        }

        // Big jumps to move i close to its target position
        while (pos[i] - x + 1 >= i) {
            apply_op(pos[i] - x + 1, pos[i], 1);
        }

        // Small shifts to place i correctly
        if (pos[i] > i) {
            int l, r;
            if (i + x - 1 <= n) {
                l = i;
                r = i + x - 1;
            } else {
                l = n - x + 1;
                r = n;
            }
            
            while(pos[i] != i) {
                apply_op(l, r, 0);
            }
        }
    }
    
    std::cout << x << " " << operations.size() << "\n";
    for (const auto& op : operations) {
        std::cout << std::get<0>(op) << " " << std::get<1>(op) << " " << std::get<2>(op) << "\n";
    }

    return 0;
}