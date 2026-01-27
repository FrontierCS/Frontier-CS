#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if(!(cin >> t)) return 0;
    vector<string> small = {
        "0   0   000 ",
        "00 00  0   0",
        "0 0 0  0   0",
        "0 0 0  0000 ",
        "0 0 0  0    ",
        "0   0  0    ",
        "0  0   00000",
        "0 0      0  ",
        "00   0 0 0  ",
        "0 0  0 0 0  ",
        "0  0 000 0  ",
        "0           "
    };
    vector<string> large = {
        "1   1   111 ",
        "11 11  1   1",
        "1 1 1  1   1",
        "1 1 1  1111 ",
        "1 1 1  1    ",
        "1   1  1    ",
        "1  1   11111",
        "1 1      1  ",
        "11   1 1 1  ",
        "1 1  1 1 1  ",
        "1  1 111 1  ",
        "1           "
    };
    const auto &out = (t==0)? small : large;
    for (int i=0;i<12;i++) cout << out[i] << "\n";
    return 0;
}