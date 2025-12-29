#include <bits/stdc++.h>
using namespace std;

bool adj[101][101];

int main() {
    memset(adj, 0, sizeof(adj));

    // First 5 vertices: query all triples
    vector<tuple<int, int, int>> triples;
    for (int a = 1; a <= 5; ++a) {
        for (int b = a + 1; b <= 5; ++b) {
            for (int c = b + 1; c <= 5; ++c) {
                triples.emplace_back(a, b, c);
            }
        }
    }
    vector<int> responses(10);
    for (int i = 0; i < 10; ++i) {
        auto [a, b, c] = triples[i];
        cout << "? " << a << " " << b << " " << c << endl;
        cout.flush();
        cin >> responses[i];
    }

    // Enumerate possible graphs for first 5
    vector<pair<int, int>> edge_list = {{1,2}, {1,3}, {1,4}, {1,5}, {2,3}, {2,4}, {2,5}, {3,4}, {3,5}, {4,5}};
    int num_cand = 0;
    int best_mask = -1;
    for (int mask = 0; mask < (1 << 10); ++mask) {
        bool temp[6][6] = {0};
        for (int k = 0; k < 10; ++k) {
            if (mask & (1 << k)) {
                int u = edge_list[k].first, v = edge_list[k].second;
                temp[u][v] = temp[v][u] = 1;
            }
        }
        bool match = true;
        int idx = 0;
        for (auto tr : triples) {
            auto [a, b, c] = tr;
            int s = temp[a][b] + temp[a][c] + temp[b][c];
            if (s != responses[idx++]) {
                match = false;
                break;
            }
        }
        if (match) {
            ++num_cand;
            best_mask = mask;
        }
    }
    // Assume exactly one candidate
    assert(num_cand == 1);
    for (int k = 0; k < 10; ++k) {
        if (best_mask & (1 << k)) {
            int u = edge_list[k].first, v = edge_list[k].second;
            adj[u][v] = adj[v][u] = 1;
        }
    }

    // Now add vertices 6 to 100
    for (int m = 6; m <= 100; ++m) {
        int ref = 1;
        int p = m - 1;
        vector<int> t(p + 1, -1); // t[1 to p], but use 2 to p
        bool all_one = true;
        bool has_zero = false;
        bool has_two = false;
        for (int j = 2; j <= p; ++j) {
            cout << "? " << ref << " " << j << " " << m << endl;
            cout.flush();
            int resp;
            cin >> resp;
            t[j] = resp - (adj[ref][j] ? 1 : 0);
            if (t[j] == 0) has_zero = true;
            if (t[j] == 2) has_two = true;
            if (t[j] != 1) all_one = false;
        }
        vector<int> x(p + 1, -1);
        if (has_zero && has_two) {
            // Impossible, assume not
            assert(false);
        } else if (has_zero) {
            x[ref] = 0;
            for (int j = 2; j <= p; ++j) {
                if (t[j] == 0) x[j] = 0;
                else if (t[j] == 1) x[j] = 1;
                else assert(false); // t==2 impossible
            }
        } else if (has_two) {
            x[ref] = 1;
            for (int j = 2; j <= p; ++j) {
                if (t[j] == 2) x[j] = 1;
                else if (t[j] == 1) x[j] = 0;
                else assert(false); // t==0 impossible
            }
        } else { // all_one
            // Extra query
            int a = 2, b = 3;
            cout << "? " << a << " " << b << " " << m << endl;
            cout.flush();
            int resp;
            cin >> resp;
            int extra = resp - (adj[a][b] ? 1 : 0);
            if (extra == 0) {
                x[ref] = 1;
                for (int j = 2; j <= p; ++j) x[j] = 0;
            } else if (extra == 2) {
                x[ref] = 0;
                for (int j = 2; j <= p; ++j) x[j] = 1;
            } else {
                assert(false); // impossible
            }
        }
        // Set adj
        for (int j = 1; j <= p; ++j) {
            adj[m][j] = x[j];
            adj[j][m] = x[j];
        }
    }

    // Output
    cout << "!" << endl;
    for (int i = 1; i <= 100; ++i) {
        for (int j = 1; j <= 100; ++j) {
            cout << (adj[i][j] ? '1' : '0');
        }
        cout << endl;
    }
    cout.flush();
    return 0;
}