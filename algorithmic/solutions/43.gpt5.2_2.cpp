#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 6, M = 7;
    vector<string> g = {
        "SS.....",
        "SS.....",
        "BB.....",
        "BB.....",
        ".......",
        "P......"
    };
    cout << N << " " << M << "\n";
    for (auto &row : g) cout << row << "\n";
    return 0;
}