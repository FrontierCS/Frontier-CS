#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    string s;
    cin >> s;
    int n = s.size();
    
    vector<int> pos;
    pos.reserve(n);
    for (int i = 0; i < n; ++i) {
        if (s[i] == '1') {
            pos.push_back(i + 1);
        }
    }
    
    int m = pos.size();
    int maxX = 0;
    while ((maxX + 1) * (maxX + 1) + (maxX + 1) <= n) {
        ++maxX;
    }
    
    long long ans = 0;
    for (int x = 1; x <= maxX; ++x) {
        int L = x * x + x;
        int max_start = n - L + 1;
        const int* p = pos.data();
        for (int i = 0; i + x - 1 < m; ++i) {
            int a = p[i];
            int b = p[i + x - 1];
            if (b - a > L - 1) continue;
            
            int prev = (i == 0 ? 0 : p[i - 1]);
            int next = (i + x == m ? n + 1 : p[i + x]);
            
            int low = prev + 1;
            int tmp = b - L + 1;
            if (low < tmp) low = tmp;
            if (low < 1) low = 1;
            
            int high = a;
            tmp = next - L;
            if (high > tmp) high = tmp;
            if (high > max_start) high = max_start;
            
            if (low <= high) {
                ans += (high - low + 1);
            }
        }
    }
    
    cout << ans << endl;
    return 0;
}