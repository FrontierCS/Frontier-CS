#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

vector<pair<int,int>> moves;

void hanoi(int n, int from, int to, int aux) {
    if (n == 0) return;
    hanoi(n - 1, from, aux, to);
    moves.emplace_back(from, to);
    hanoi(n - 1, aux, to, from);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;

    hanoi(N, 1, 3, 2);
    cout << moves.size() << "\n";
    for (auto &p : moves) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}