#include <bits/stdc++.h>
using namespace std;

const int MAXN = 2000005;
unsigned char a[MAXN];
int pre[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    if (!(cin >> s)) return 0;
    int n = (int)s.size();
    if (n == 0) {
        cout << 0 << '\n';
        return 0;
    }

    for (int i = 0; i < n; ++i) {
        a[i] = (s[i] == '1');
        pre[i + 1] = pre[i] + a[i];
    }

    int totalOnes = pre[n];
    long long ans = 0;

    int k = 1;
    int len = 2; // k*(k+1) for k = 1
    while (k <= totalOnes && len <= n) {
        int ones = pre[len];  // ones in [0, len)
        int start = 0, end = len;
        while (true) {
            if (ones == k) ++ans;
            if (end == n) break;
            ones += (int)a[end] - (int)a[start];
            ++start;
            ++end;
        }
        ++k;
        len += 2 * k; // len_{k} = k*(k+1); increment by 2k each step
    }

    cout << ans << '\n';
    return 0;
}