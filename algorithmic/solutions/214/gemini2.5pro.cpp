#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <sstream>

// current sequence
std::vector<int> a;
// pos[v] = 1-based index of value v
std::vector<int> pos;
// operations
std::vector<std::pair<int, int>> ops;

void apply_reverse(int l, int r) {
    if (l > r) std::swap(l, r);
    ops.push_back({l, r});
    // The internal representation `a` is 0-indexed.
    // So we operate on indices l-1 to r-1.
    std::reverse(a.begin() + l - 1, a.begin() + r);
    for (int i = l; i <= r; ++i) {
        pos[a[i - 1]] = i;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;
    a.resize(n);
    pos.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
        pos[a[i]] = i + 1;
    }
    
    // Choose x. To sort any permutation, we may need to change the parity of an
    // element's position. This is possible only with even-length reversals.
    // Choosing an odd x gives even lengths L1=x-1, L2=x+1.
    // x=3 gives L=2,4, which are small and versatile.
    int x = 3;

    // Place elements from n down to 1 into their correct positions.
    for (int i = n; i >= 1; --i) {
        int p = pos[i];
        while (p < i) {
            // Move value i from p towards i.
            // We can move it by 1 or 3 positions forward using a reversal of
            // length 2 or 4 starting at p.
            if (p + 3 <= i) {
                // Use reversal of length 4 to move a[p] to p+3
                apply_reverse(p, p + 3);
            } else {
                // Use reversal of length 2 to move a[p] to p+1
                apply_reverse(p, p + 1);
            }
            p = pos[i]; // Update current position of i
        }
    }

    std::cout << x << "\n";
    std::cout << ops.size() << "\n";
    for (const auto& op : ops) {
        std::cout << op.first << " " << op.second << "\n";
    }

    return 0;
}