#include <bits/stdc++.h>
using namespace std;

const int R = 8;
const int C = 14;
int grid[R][C];
vector<pair<int, int>> neighbors[R][C];

void precompute_neighbors() {
    int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};
    int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            for (int d = 0; d < 8; ++d) {
                int ni = i + dr[d];
                int nj = j + dc[d];
                if (ni >= 0 && ni < R && nj >= 0 && nj < C) {
                    neighbors[i][j].emplace_back(ni, nj);
                }
            }
        }
    }
}

struct Score {
    int pairs;   // number of covered pairs (a,b) with a=1..9, b=0..9
    int triples; // number of covered triples (a,b,c) with a=1..9, b,c=0..9
    bool operator>(const Score& other) const {
        if (pairs != other.pairs) return pairs > other.pairs;
        return triples > other.triples;
    }
    bool operator>=(const Score& other) const {
        return pairs > other.pairs || (pairs == other.pairs && triples >= other.triples);
    }
};

Score evaluate() {
    static bool pair_covered[10][10] = {{false}};
    static bool triple_covered[10][10][10] = {{{false}}};
    memset(pair_covered, 0, sizeof(pair_covered));
    memset(triple_covered, 0, sizeof(triple_covered));

    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            int b = grid[i][j];
            vector<int> neigh_digits;
            for (auto& p : neighbors[i][j]) {
                int d = grid[p.first][p.second];
                neigh_digits.push_back(d);
                pair_covered[d][b] = true;
            }
            for (int a : neigh_digits) {
                for (int c : neigh_digits) {
                    triple_covered[a][b][c] = true;
                }
            }
        }
    }

    int pair_count = 0;
    for (int a = 1; a <= 9; ++a)
        for (int b = 0; b <= 9; ++b)
            if (pair_covered[a][b]) pair_count++;

    int triple_count = 0;
    for (int a = 1; a <= 9; ++a)
        for (int b = 0; b <= 9; ++b)
            for (int c = 0; c <= 9; ++c)
                if (triple_covered[a][b][c]) triple_count++;

    return {pair_count, triple_count};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    precompute_neighbors();
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dig(0, 9);

    // random initial grid
    for (int i = 0; i < R; ++i)
        for (int j = 0; j < C; ++j)
            grid[i][j] = dig(rng);

    Score best_score = evaluate();
    int best_grid[R][C];
    memcpy(best_grid, grid, sizeof(grid));

    const double start_temp = 1.0;
    const double end_temp = 0.0001;
    const long long max_iterations = 5000000;
    long long iterations = 0;
    auto start_time = chrono::steady_clock::now();

    while (true) {
        ++iterations;
        if (iterations % 10000 == 0) {
            auto now = chrono::steady_clock::now();
            auto elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > 55.0) break; // stop after 55 seconds
        }

        int r = uniform_int_distribution<int>(0, R - 1)(rng);
        int c = uniform_int_distribution<int>(0, C - 1)(rng);
        int old_digit = grid[r][c];
        int new_digit;
        do {
            new_digit = dig(rng);
        } while (new_digit == old_digit);

        grid[r][c] = new_digit;
        Score new_score = evaluate();

        bool accept = false;
        if (new_score >= best_score) {
            accept = true;
        } else {
            double progress = min(1.0, (double)iterations / max_iterations);
            double temperature = start_temp * pow(end_temp / start_temp, progress);
            double delta = (new_score.pairs - best_score.pairs) * 1000000.0 +
                           (new_score.triples - best_score.triples);
            if (uniform_real_distribution<double>(0, 1)(rng) < exp(delta / temperature)) {
                accept = true;
            }
        }

        if (accept) {
            best_score = new_score;
            memcpy(best_grid, grid, sizeof(grid));
        } else {
            grid[r][c] = old_digit; // revert
        }
    }

    // output best grid
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            cout << char('0' + best_grid[i][j]);
        }
        cout << '\n';
    }
    cout.flush();

    return 0;
}