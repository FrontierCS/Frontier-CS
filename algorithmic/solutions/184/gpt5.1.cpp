#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N);
    vector<int> deg(N, 0);

    for (long long i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        deg[u]++; deg[v]++;
    }

    vector<int> vertices(N);
    iota(vertices.begin(), vertices.end(), 0);

    vector<unsigned long long> rand_key(N);
    vector<char> best_selected(N, 0);
    int best_size = 0;

    int R;
    if (M <= 200000) R = 700;
    else if (M <= 400000) R = 400;
    else R = 250;

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto start = chrono::steady_clock::now();

    vector<char> banned(N), selected(N);

    for (int it = 0; it < R; ++it) {
        if (it % 10 == 0) {
            auto now = chrono::steady_clock::now();
            auto elapsed = chrono::duration_cast<chrono::milliseconds>(now - start).count();
            if (elapsed > 1800) break;
        }

        int mode = it % 3;
        for (int i = 0; i < N; ++i) rand_key[i] = rng();

        if (mode == 0) { // ascending degree
            sort(vertices.begin(), vertices.end(), [&](int a, int b) {
                if (deg[a] != deg[b]) return deg[a] < deg[b];
                return rand_key[a] < rand_key[b];
            });
        } else if (mode == 1) { // descending degree
            sort(vertices.begin(), vertices.end(), [&](int a, int b) {
                if (deg[a] != deg[b]) return deg[a] > deg[b];
                return rand_key[a] < rand_key[b];
            });
        } else { // purely random
            shuffle(vertices.begin(), vertices.end(), rng);
        }

        fill(banned.begin(), banned.end(), 0);
        fill(selected.begin(), selected.end(), 0);
        int cur_size = 0;

        for (int vtx : vertices) {
            if (banned[vtx]) continue;
            selected[vtx] = 1;
            ++cur_size;
            banned[vtx] = 1;
            for (int nb : adj[vtx]) {
                banned[nb] = 1;
            }
        }

        if (cur_size > best_size) {
            best_size = cur_size;
            best_selected = selected;
        }
    }

    // Final safety check to ensure independence (in case of unforeseen bugs).
    vector<char> independent = best_selected;
    for (int v = 0; v < N; ++v) {
        if (!independent[v]) continue;
        for (int nb : adj[v]) {
            if (independent[nb]) {
                independent[nb] = 0;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << (independent[i] ? 1 : 0) << '\n';
    }

    return 0;
}