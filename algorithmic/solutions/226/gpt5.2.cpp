#include <bits/stdc++.h>
using namespace std;

static inline long long weight_of(int node, long long n, int L) {
    long long pos = (long long)node + 1; // actual number in first block
    if (pos > n) return 0LL;
    return 1LL + (n - pos) / (long long)L;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    int x, y;
    cin >> n >> x >> y;

    int L = x + y;
    int g = std::gcd(L, x);
    int len = L / g;

    auto next_node = [&](int node) -> int {
        node += x;
        if (node >= L) node -= L;
        return node;
    };

    long long ans = 0;

    for (int s = 0; s < g; s++) {
        if (len == 1) {
            ans += weight_of(s, n, L);
            continue;
        }

        int v0 = s;
        int v1 = next_node(v0);

        if (len == 2) {
            long long w0 = weight_of(v0, n, L);
            long long w1 = weight_of(v1, n, L);
            ans += max(w0, w1);
            continue;
        }

        // Case A: exclude v0 => path v1..v_{len-1}
        long long dpA_prev2 = 0;
        long long dpA_prev1 = weight_of(v1, n, L);
        int node = v1;
        for (int i = 2; i <= len - 1; i++) {
            node = next_node(node);
            long long w = weight_of(node, n, L);
            long long cur = max(dpA_prev1, dpA_prev2 + w);
            dpA_prev2 = dpA_prev1;
            dpA_prev1 = cur;
        }
        long long bestA = dpA_prev1;

        // Case B: include v0 => w0 + path v2..v_{len-2}
        long long w0 = weight_of(v0, n, L);
        long long bestB = w0;

        if (len == 4) {
            int v2 = next_node(v1);
            bestB = w0 + weight_of(v2, n, L);
        } else if (len >= 5) {
            int v2 = next_node(v1);
            long long dpB_prev2 = 0;
            long long dpB_prev1 = weight_of(v2, n, L);
            node = v2;
            for (int i = 3; i <= len - 2; i++) {
                node = next_node(node);
                long long w = weight_of(node, n, L);
                long long cur = max(dpB_prev1, dpB_prev2 + w);
                dpB_prev2 = dpB_prev1;
                dpB_prev1 = cur;
            }
            bestB = w0 + dpB_prev1;
        }

        ans += max(bestA, bestB);
    }

    cout << ans << "\n";
    return 0;
}