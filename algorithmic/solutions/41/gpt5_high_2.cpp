#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    unsigned long long n;
    if(!(cin >> n)) return 0;

    vector<unsigned long long> seq;
    unsigned long long x = 1;
    seq.push_back(x);
    while (x <= n / 2) {
        x *= 2;
        seq.push_back(x);
    }

    cout << seq.size() << "\n";
    for (size_t i = 0; i < seq.size(); ++i) {
        if (i) cout << ' ';
        cout << seq[i];
    }
    cout << "\n";
    return 0;
}