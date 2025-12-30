#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long subtask;
    int n;
    if (!(cin >> subtask >> n)) return 0;
    
    cout << -1;
    for (int i = 1; i <= n; ++i) {
        cout << " " << i;
    }
    cout << "\n";
    cout.flush();
    return 0;
}