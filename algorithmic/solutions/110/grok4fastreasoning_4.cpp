#include <bits/stdc++.h>
using namespace std;

int main() {
    vector<string> grid = {
        "10203344536473",
        "01020102010201",
        "00000000008390",
        "00000000000400",
        "00000000000000",
        "55600000000089",
        "78900066000089",
        "00000789000077"
    };
    for (const auto& row : grid) {
        cout << row << endl;
    }
    return 0;
}