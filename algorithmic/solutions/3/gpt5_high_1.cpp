#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long subtask, n;
    if (!(cin >> subtask)) return 0;
    if (!(cin >> n)) {
        n = subtask;
    }
    
    cout << -1;
    for (long long i = 1; i <= n; ++i) {
        cout << " " << i;
    }
    cout << "\n";
    cout.flush();
    return 0;
}