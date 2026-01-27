#include <bits/stdc++.h>
using namespace std;

int n;
unordered_map<long long, int> memo;

long long keyLR(int l, int r) {
    return ((long long)l << 21) ^ r; // n<=2000, safe packing
}

int getInv(int l, int r) {
    if (l >= r) return 0; // length 0 or 1 has zero inversions
    long long k = keyLR(l, r);
    auto it = memo.find(k);
    if (it != memo.end()) return it->second;
    cout << "0 " << l << " " << r << "\n";
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    memo[k] = ans & 1;
    return memo[k];
}

int pairCmpMinMax(int a, int b) {
    // assumes a < b, returns [p_a > p_b] mod 2
    int s1 = getInv(a, b);
    int s2 = getInv(a + 1, b);
    int s3 = getInv(a, b - 1);
    int s4 = getInv(a + 1, b - 1);
    return (s1 ^ s2 ^ s3 ^ s4) & 1;
}

bool greaterXY(int x, int y) {
    if (x == y) return false;
    int a = min(x, y), b = max(x, y);
    int bit = pairCmpMinMax(a, b);
    if (x == a) {
        // returns [p_x > p_y]
        return bit == 1;
    } else {
        // we have [p_a > p_b] == [p_y > p_x], so invert
        return bit == 0;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;

    vector<int> order;
    order.reserve(n);
    for (int i = 1; i <= n; ++i) {
        int lo = 0, hi = (int)order.size(); // insert position
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            // if p_i > p_order[mid], go right
            if (greaterXY(i, order[mid])) lo = mid + 1;
            else hi = mid;
        }
        order.insert(order.begin() + lo, i);
    }

    vector<int> p(n + 1, 0);
    for (int rank = 0; rank < n; ++rank) {
        p[order[rank]] = rank + 1;
    }

    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << "\n";
    cout.flush();

    return 0;
}