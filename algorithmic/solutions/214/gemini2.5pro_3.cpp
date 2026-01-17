#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

struct Operation {
    int l, r;
};

int n;
std::vector<int> a;
std::vector<int> pos;
std::vector<Operation> ops;
int L1, L2;

void do_rev(int l, int r) {
    if (l >= r || l < 1 || r > n) return;
    ops.push_back({l, r});
    std::reverse(a.begin() + l - 1, a.begin() + r);
    for (int i = l; i <= r; ++i) {
        pos[a[i - 1]] = i;
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

    int x;
    if (n <= 3) {
        x = n - 1;
        if (x == 0) x = 1;
    } else {
        if (n % 2 == 0) {
            x = n - 1;
        } else {
            x = n;
        }
    }
    
    L1 = x - 1;
    L2 = x + 1;

    for (int i = 1; i <= n; ++i) {
        int p = pos[i];
        if (p == i) continue;

        if (p > i) {
            int len = p - i + 1;
            if (len == L1 || len == L2) {
                do_rev(i, p);
                continue;
            }
            if (L2 <= n && i + L2 - 1 <= n) {
                do_rev(i, i + L2 - 1);
            } else if (L1 > 0 && i + L1 - 1 <= n) {
                do_rev(i, i + L1 - 1);
            } else {
                if (L2 <= n && p - L2 + 1 >= 1) {
                    do_rev(p - L2 + 1, p);
                } else if (L1 > 0 && p - L1 + 1 >= 1) {
                    do_rev(p - L1 + 1, p);
                } else {
                    if (L2 <= n) do_rev(1, L2);
                    else if (L1 > 0) do_rev(1, L1);
                }
            }
            i--;
        } else { // p < i
            int len = i - p + 1;
            if (len == L1 || len == L2) {
                do_rev(p, i);
                continue;
            }
            if (L2 <= n && p + L2 - 1 <= n) {
                do_rev(p, p + L2 - 1);
            } else if (L1 > 0 && p + L1 - 1 <= n) {
                do_rev(p, p + L1 - 1);
            } else {
                 if (L2 <= n && i - L2 + 1 >= 1) {
                    do_rev(i - L2 + 1, i);
                } else if (L1 > 0 && i - L1 + 1 >= 1) {
                    do_rev(i - L1 + 1, i);
                } else {
                    if (L2 <= n) do_rev(n - L2 + 1, n);
                    else if (L1 > 0) do_rev(n - L1 + 1, n);
                }
            }
            i--;
        }
    }

    std::cout << x << "\n";
    std::cout << ops.size() << "\n";
    for (const auto& op : ops) {
        std::cout << op.l << " " << op.r << "\n";
    }

    return 0;
}