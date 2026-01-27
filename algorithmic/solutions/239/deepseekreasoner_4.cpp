#include <bits/stdc++.h>
using namespace std;

const int MAXN = 4097; // n <= 4096, vertices 0..4096

vector<vector<bool>> edge;
vector<tuple<int, int, int>> additions;
int N;

void ensure_edge(int a, int c) {
    if (edge[a][c]) return;
    int d = c - a;
    if (d == 1) return; // initial edge
    int b = a + d / 2;
    ensure_edge(a, b);
    ensure_edge(b, c);
    // Now edges a->b and b->c exist
    edge[a][c] = true;
    additions.emplace_back(a, b, c);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;
    N = n;
    edge.assign(n + 1, vector<bool>(n + 1, false));
    for (int i = 0; i < n; ++i) {
        edge[i][i + 1] = true; // initial edges
    }

    // compute B = ceil(cbrt(n))
    int B = 1;
    while (B * B * B < n) ++B;

    vector<int> lengths;
    // lengths 2 .. B-1
    for (int i = 2; i < B; ++i) lengths.push_back(i);
    // multiples of B: B, 2B, ..., (B-1)*B
    for (int i = 1; i < B; ++i) {
        int d = i * B;
        if (d <= n) lengths.push_back(d);
    }
    // multiples of B^2
    for (int i = 1; i < B; ++i) {
        int d = i * B * B;
        if (d <= n) lengths.push_back(d);
    }

    sort(lengths.begin(), lengths.end());
    lengths.erase(unique(lengths.begin(), lengths.end()), lengths.end());

    for (int L : lengths) {
        for (int a = 0; a + L <= n; ++a) {
            ensure_edge(a, a + L);
        }
    }

    cout << additions.size() << '\n';
    for (auto [a, b, c] : additions) {
        cout << a << ' ' << b << ' ' << c << '\n';
    }

    return 0;
}