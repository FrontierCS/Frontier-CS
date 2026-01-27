#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    // As interaction is not possible here, output a default balanced sequence of length n
    // Construct a sequence with as many balanced pairs as possible
    string s;
    int open = n / 2;
    int close = n - open;
    for (int i = 0; i < open; ++i) s.push_back('(');
    for (int i = 0; i < close; ++i) s.push_back(')');
    cout << "1 " << s << endl;
    cout.flush();
    return 0;
}