#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cassert>

std::vector<int> a;
std::vector<std::pair<int, int>> ops;
int n;
int x;
int len1, len2;

// Apply a reversal and record it.
void apply_reverse(int l, int r) {
    if (l < 1 || r > n || l >= r) {
        return;
    }
    ops.push_back({l, r});
    std::reverse(a.begin() + l - 1, a.begin() + r);
}

// Find the 1-based position of a value.
int find_pos(int val) {
    for (int i = 0; i < n; ++i) {
        if (a[i] == val) {
            return i + 1;
        }
    }
    return -1;
}

// Move element at p left by 2 positions.
// This is done by a reverse of length x-1 followed by one of length x+1.
void move_left_2(int p, int val_to_move) {
    apply_reverse(p, p + len2 - 1);
    int new_p = find_pos(val_to_move);
    apply_reverse(new_p - len1 + 1, new_p);
}

// Move element at p right by 2 positions.
// This is done by a reverse of length x+1 followed by one of length x-1.
void move_right_2(int p, int val_to_move) {
    apply_reverse(p - len1 + 1, p);
    int new_p = find_pos(val_to_move);
    apply_reverse(new_p, new_p + len2 - 1);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    std::cin >> n;
    a.resize(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
    }

    if (n == 1) {
        std::cout << 1 << std::endl;
        std::cout << 0 << std::endl;
        return 0;
    }

    // Choose x to be an odd integer around n/3, with special handling for small n.
    x = n / 3;
    if (x % 2 == 0) x++;
    if (x <= 0) x = 1;
    if (n <= 5) {
        if (n==2) x=1;
        else if (n==3) x=3;
        else if (n==4) x=3;
        else if (n==5) x=3;
    }


    len1 = x + 1;
    len2 = x - 1;

    for (int i = 1; i <= n; ++i) {
        int p = find_pos(i);
        if (p == i) continue;

        // If distance p-i has wrong parity, fix it with one odd-length reversal.
        if ((p - i) % 2 != 0) {
            if (p + len2 - 1 <= n) {
                apply_reverse(p, p + len2 - 1);
            } else {
                apply_reverse(p - len2 + 1, p);
            }
        }
        
        p = find_pos(i);
        while (p != i) {
            if (p > i) {
                // Try to move left by 2
                if (p - 2 >= i && p + len2 - 1 <= n) {
                    move_left_2(p, i);
                } else { // Cannot move left by 2, use a single large reversal
                    if (p - len1 + 1 >= i) {
                        apply_reverse(p - len1 + 1, p);
                    } else {
                        apply_reverse(i, i + len1 - 1);
                    }
                }
            } else { // p < i
                // Try to move right by 2
                if (p + 2 <= i && p - len1 + 1 >= 1) {
                     move_right_2(p, i);
                } else { // Cannot move right by 2, use a single large reversal
                    if (p + len1 - 1 <= n) {
                        apply_reverse(p, p + len1 - 1);
                    } else {
                        apply_reverse(n - len1 + 1, n);
                    }
                }
            }
            p = find_pos(i);
        }
    }

    std::cout << x << std::endl;
    std::cout << ops.size() << std::endl;
    for (const auto& op : ops) {
        std::cout << op.first << " " << op.second << std::endl;
    }

    return 0;
}