#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;

    string s;
    s.reserve(n);
    for (int i = 0; i < n; ++i) {
        s.push_back(i % 2 == 0 ? '(' : ')');
    }

    cout << "1 " << s << "\n";
    cout.flush();
    return 0;
}