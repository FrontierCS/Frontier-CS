#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

struct Operation {
    int l, r, dir;
};

int n;
std::vector<int> a;
std::vector<int> pos;
std::vector<Operation> ops;

void apply_left_shift(int l, int r) {
    ops.push_back({l, r, 0});
    int val_l = a[l];
    for (int i = l; i < r; ++i) {
        a[i] = a[i + 1];
        pos[a[i]] = i;
    }
    a[r] = val_l;
    pos[a[r]] = r;
}

void apply_right_shift(int l, int r) {
    ops.push_back({l, r, 1});
    int val_r = a[r];
    for (int i = r; i > l; --i) {
        a[i] = a[i - 1];
        pos[a[i]] = i;
    }
    a[l] = val_r;
    pos[a[l]] = l;
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

    if (n == 1) {
        std::cout << "1 0\n";
        return 0;
    }

    int x;
    if (n <= 5) {
        if (n == 2) x = 2;
        else if (n == 3) x = 3;
        else if (n == 4) x = 3;
        else x = 3; // n=5 from sample
    } else {
        x = static_cast<int>(std::round(std::sqrt(n / 2.0)));
        if (x < 2) x = 2;
    }
    
    for (int i = 1; i <= n; ++i) {
        int current_p = pos[i];
        if (current_p == i) {
            continue;
        }

        while (current_p - x + 1 >= i) {
            apply_right_shift(current_p - x + 1, current_p);
            current_p = pos[i];
        }
        
        if (current_p == i) continue;

        if (current_p > i) {
            int dist = current_p - i;
            if (i + x - 1 <= n) {
                for(int k=0; k<dist; ++k) {
                   apply_left_shift(i, i + x - 1);
                }
            } else {
                 for(int k=0; k<dist; ++k) {
                    apply_left_shift(n - x + 1, n);
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