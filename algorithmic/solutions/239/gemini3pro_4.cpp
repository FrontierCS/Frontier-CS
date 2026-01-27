#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

struct Edge {
    int u, c, v;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;
    if (n == 0) {
        cout << 0 << "\n";
        return 0;
    }

    // We want to cover distances up to n using at most 3 edges.
    // This suggests a 3-layer structure (like base representation).
    // Optimal base B is approximately n^(1/3).
    int B = 1;
    while (B * B * B < n) {
        B++;
    }
    // Ensure B is at least 2 to avoid infinite loops or logic errors for small n.
    if (B < 2) B = 2;

    vector<Edge> result;

    // Layer 0: Construct lengths 2, 3, ..., B-1.
    // Length 1 is already present.
    // Formula: k = 1 + (k-1)
    for (int len = 2; len < B; ++len) {
        if (len > n) break;
        int seg1 = 1;
        int seg2 = len - 1;
        for (int u = 0; u <= n - len; ++u) {
            result.push_back({u, u + seg1, u + len});
        }
    }

    // Layer 1: Construct lengths B, 2B, ..., (B-1)B.
    // Base case: B = 1 + (B-1). 
    // (B-1) is the largest length from Layer 0 (or 1 if B=2).
    // Inductive step: kB = B + (k-1)B.
    if (B <= n) {
        int seg1 = 1;
        int seg2 = B - 1;
        for (int u = 0; u <= n - B; ++u) {
            result.push_back({u, u + seg1, u + B});
        }
    }
    
    for (int k = 2; k < B; ++k) {
        int len = k * B;
        if (len > n) break;
        int seg1 = B;
        int seg2 = (k - 1) * B;
        for (int u = 0; u <= n - len; ++u) {
            result.push_back({u, u + seg1, u + len});
        }
    }

    // Layer 2: Construct lengths B^2, 2B^2, ..., until N.
    // Base case: B^2 = B + (B-1)B.
    // B is start of Layer 1, (B-1)B is end of Layer 1.
    // Inductive step: kB^2 = B^2 + (k-1)B^2.
    int B2 = B * B;
    if (B2 <= n) {
        int seg1 = B;
        int seg2 = (B - 1) * B;
        for (int u = 0; u <= n - B2; ++u) {
            result.push_back({u, u + seg1, u + B2});
        }
    }

    for (int len = 2 * B2; len <= n; len += B2) {
        int seg1 = B2;
        int seg2 = len - B2;
        for (int u = 0; u <= n - len; ++u) {
            result.push_back({u, u + seg1, u + len});
        }
    }

    cout << result.size() << "\n";
    for (const auto& e : result) {
        cout << e.u << " " << e.c << " " << e.v << "\n";
    }

    return 0;
}