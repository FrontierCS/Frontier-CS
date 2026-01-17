#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <tuple>

struct Operation {
    int l, r, dir;
};

std::vector<int> a;
std::vector<int> pos;
int n;
int x;
std::vector<Operation> ops;

void apply_shift(int l, int r, int dir) {
    ops.push_back({l, r, dir});
    if (dir == 0) { // left shift
        int first_val = a[l - 1];
        for (int i = l; i < r; ++i) {
            a[i - 1] = a[i];
            pos[a[i - 1]] = i;
        }
        a[r - 1] = first_val;
        pos[first_val] = r;
    } else { // right shift
        int last_val = a[r - 1];
        for (int i = r - 1; i > l - 1; --i) {
            a[i] = a[i - 1];
            pos[a[i]] = i + 1;
        }
        a[l - 1] = last_val;
        pos[last_val] = l;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;
    a.resize(n);
    pos.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
        pos[a[i]] = i + 1;
    }

    if (n == 1) {
        std::cout << "1 0\n";
        return 0;
    }
    
    x = static_cast<int>(floor(sqrt(n - 1))) + 1;
    if (x == 1 && n > 1) {
        x = 2;
    }

    for (int i = 1; i <= n; ++i) {
        int current_pos = pos[i];
        if (current_pos == i) {
            continue;
        }

        if (current_pos > i) {
            while (current_pos - (x - 1) >= i) {
                int l = current_pos - x + 1;
                int r = current_pos;
                apply_shift(l, r, 1); // right shift
                current_pos = l;
            }

            if (current_pos > i) {
                int dist = current_pos - i;
                if (i + x - 1 <= n) {
                    int l = i;
                    int r = i + x - 1;
                    for (int k = 0; k < dist; ++k) {
                        apply_shift(l, r, 0); // left shift
                    }
                } else {
                    int l = current_pos - x + 1;
                    int r = current_pos;
                    for (int k = 0; k < dist; ++k) {
                        apply_shift(l, r, 0); // left shift
                    }
                }
            }
        } else { // current_pos < i
            while (current_pos + (x - 1) <= i) {
                int l = current_pos;
                int r = current_pos + x - 1;
                apply_shift(l, r, 0); // left shift
                current_pos = r;
            }

            if (current_pos < i) {
                int dist = i - current_pos;
                 if (i - x + 1 >= 1) {
                    int l = i - x + 1;
                    int r = i;
                     for (int k = 0; k < dist; ++k) {
                        apply_shift(l, r, 1); // right shift
                    }
                } else {
                    int l = current_pos;
                    int r = current_pos + x - 1;
                    for (int k = 0; k < dist; ++k) {
                        apply_shift(l, r, 1); // right shift
                    }
                }
            }
        }
    }

    std::cout << x << " " << ops.size() << "\n";
    for (const auto& op : ops) {
        std::cout << op.l << " " << op.r << " " << op.dir << "\n";
    }

    return 0;
}