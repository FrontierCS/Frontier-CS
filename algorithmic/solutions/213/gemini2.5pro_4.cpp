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
std::vector<int> where;
std::vector<Operation> ops;
int x;

void left_shift(int l, int r) {
    ops.push_back({l, r, 0});
    int first_val = a[l];
    for (int i = l; i < r; ++i) {
        a[i] = a[i + 1];
        where[a[i]] = i;
    }
    a[r] = first_val;
    where[a[r]] = r;
}

void right_shift(int l, int r) {
    ops.push_back({l, r, 1});
    int last_val = a[r];
    for (int i = r; i > l; --i) {
        a[i] = a[i - 1];
        where[a[i]] = i;
    }
    a[l] = last_val;
    where[a[l]] = l;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;
    a.resize(n + 1);
    where.resize(n + 1);
    for (int i = 1; i <= n; ++i) {
        std::cin >> a[i];
        where[a[i]] = i;
    }

    x = (n / 2) + 1;

    for (int i = 1; i <= n / 2; ++i) {
        int pos = where[i];
        if (pos == i) {
            continue;
        }

        while (pos - i >= x - 1) {
            right_shift(pos - x + 1, pos);
            pos = where[i];
        }

        if (pos > i) {
            int dist = pos - i;
            for (int k = 0; k < dist; ++k) {
                left_shift(i, i + x - 1);
            }
        }
    }

    for (int i = n; i > n / 2; --i) {
        int pos = where[i];
        if (pos == i) {
            continue;
        }

        while (i - pos >= x - 1) {
            left_shift(pos, pos + x - 1);
            pos = where[i];
        }

        if (pos < i) {
            int dist = i - pos;
            for (int k = 0; k < dist; ++k) {
                right_shift(i - x + 1, i);
            }
        }
    }

    std::cout << x << " " << ops.size() << "\n";
    for (const auto& op : ops) {
        std::cout << op.l << " " << op.r << " " << op.dir << "\n";
    }

    return 0;
}