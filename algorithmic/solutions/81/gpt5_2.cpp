#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    string S;
    if (!(cin >> S)) {
        S = string(N, '0');
    }
    cout << 0 << "\n" << S << "\n";
    return 0;
}