#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    int x, y;
    if (!(cin >> n >> x >> y)) return 0;
    if (n <= 0) {
        cout << 0;
        return 0;
    }
    
    if (x > y) swap(x, y);
    
    // If both distances are larger than the segment, no forbidden pairs exist
    if (x > n - 1 && y > n - 1) {
        cout << n;
        return 0;
    }
    
    int L = max(x, y);
    vector<unsigned char> last(L, 0);
    
    long long M = n;
    long long minSteps = 3LL * L;
    if (minSteps < 3000000LL) minSteps = 3000000LL;
    if (M > minSteps) M = minSteps;
    if (M > 20000000LL) M = 20000000LL;
    
    int steps = (int)M;
    long long chooseCount = 0;
    int idx = 0;
    
    for (int i = 1; i <= steps; ++i) {
        if (idx == L) idx = 0;
        
        bool px = false, py = false;
        if (i > x) {
            int px_idx = idx - x;
            if (px_idx < 0) px_idx += L;
            px = last[px_idx];
        }
        if (i > y) {
            int py_idx = idx - y;
            if (py_idx < 0) py_idx += L;
            py = last[py_idx];
        }
        
        unsigned char cur = (!px && !py) ? 1 : 0;
        last[idx] = cur;
        chooseCount += cur;
        ++idx;
    }
    
    long long ans;
    if (M == n) {
        ans = chooseCount;
    } else {
        long double density = (long double)chooseCount / (long double)M;
        long double est = density * (long double)n;
        ans = (long long)(est + 0.5L);
        if (ans < 0) ans = 0;
        if (ans > n) ans = n;
    }
    
    cout << ans;
    return 0;
}