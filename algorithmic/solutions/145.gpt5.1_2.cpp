#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    string row;
    if (n == 0) {
        row = "012301230123";
    } else {
        row = "123123123123";
    }

    for (int i = 0; i < 12; ++i) {
        cout << row << '\n';
    }

    return 0;
}