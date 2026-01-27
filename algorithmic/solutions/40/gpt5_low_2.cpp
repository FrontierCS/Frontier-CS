#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    
    string s;
    int pairs = n / 2;
    s.reserve(n);
    for (int i = 0; i < pairs; ++i) s += "()";
    if ((int)s.size() > n) s.resize(n);
    while ((int)s.size() < n) s += '('; // pad if odd (arbitrary)
    
    cout << "1 " << s << "\n";
    cout.flush();
    return 0;
}