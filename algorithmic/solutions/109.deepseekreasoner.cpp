#include <iostream>
#include <vector>
#include <algorithm>
#include <stack>
#include <tuple>

using namespace std;

// Knight moves
const int moves[8][2] = {{2,1},{2,-1},{-2,1},{-2,-1},{1,2},{1,-2},{-1,2},{-1,-2}};

struct State {
    int r, c;
    vector<pair<int,int>> cand;  // sorted candidate moves
    int idx;                     // next candidate index to try
};

// Check if (r,c) is inside board (0-indexed)
inline bool inside(int r, int c, int N) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

// Compute number of unvisited neighbors from (r,c)
int degree(int r, int c, const vector<vector<bool>>& visited, int N) {
    int cnt = 0;
    for (int i = 0; i < 8; ++i) {
        int nr = r + moves[i][0];
        int nc = c + moves[i][1];
        if (inside(nr, nc, N) && !visited[nr][nc])
            ++cnt;
    }
    return cnt;
}

// Generate and sort candidate moves from (r,c) according to Warnsdorff's rule
vector<pair<int,int>> candidates(int r, int c, const vector<vector<bool>>& visited, int N) {
    vector<pair<int,int>> cand;
    for (int i = 0; i < 8; ++i) {
        int nr = r + moves[i][0];
        int nc = c + moves[i][1];
        if (inside(nr, nc, N) && !visited[nr][nc]) {
            cand.emplace_back(nr, nc);
        }
    }
    // Sort by: smaller degree first, then larger distance from center, then row, then column.
    int center = N - 1;  // 2*r - (N-1) = 2*r - center
    sort(cand.begin(), cand.end(), [&](const pair<int,int>& a, const pair<int,int>& b) {
        int da = degree(a.first, a.second, visited, N);
        int db = degree(b.first, b.second, visited, N);
        if (da != db) return da < db;
        // tie: distance from center (larger first)
        int dist_a = (2*a.first - center)*(2*a.first - center) + (2*a.second - center)*(2*a.second - center);
        int dist_b = (2*b.first - center)*(2*b.first - center) + (2*b.second - center)*(2*b.second - center);
        if (dist_a != dist_b) return dist_a > dist_b;
        // further tie: row, then column
        if (a.first != b.first) return a.first < b.first;
        return a.second < b.second;
    });
    return cand;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, sr, sc;
    cin >> N >> sr >> sc;
    // convert to 0-indexed
    sr--; sc--;

    vector<vector<bool>> visited(N, vector<bool>(N, false));
    vector<pair<int,int>> path;
    vector<pair<int,int>> best_path;
    int best_len = 0;

    // start position
    visited[sr][sc] = true;
    path.emplace_back(sr, sc);

    // initial state
    State start;
    start.r = sr;
    start.c = sc;
    start.cand = candidates(sr, sc, visited, N);
    start.idx = 0;

    stack<State> st;
    st.push(start);

    const long long MAX_OPERATIONS = 10000000; // safety limit
    long long operations = 0;
    bool found_full = false;

    while (!st.empty() && operations < MAX_OPERATIONS) {
        ++operations;
        State& top = st.top();

        if (top.idx < (int)top.cand.size()) {
            // try next candidate
            int nr = top.cand[top.idx].first;
            int nc = top.cand[top.idx].second;
            ++top.idx;

            // safety check (should be unvisited)
            if (visited[nr][nc]) continue;

            visited[nr][nc] = true;
            path.emplace_back(nr, nc);

            if ((int)path.size() == N * N) {
                found_full = true;
                break;
            }

            State next;
            next.r = nr;
            next.c = nc;
            next.cand = candidates(nr, nc, visited, N);
            next.idx = 0;
            st.push(next);
        } else {
            // no more candidates -> backtrack
            if ((int)path.size() > best_len) {
                best_len = path.size();
                best_path = path;
            }
            visited[top.r][top.c] = false;
            path.pop_back();
            st.pop();
        }
    }

    // If we broke due to operation limit, update best one last time
    if (!found_full && (int)path.size() > best_len) {
        best_len = path.size();
        best_path = path;
    }

    // Output result
    vector<pair<int,int>>& output_path = found_full ? path : best_path;
    cout << output_path.size() << '\n';
    for (auto& p : output_path) {
        cout << p.first + 1 << ' ' << p.second + 1 << '\n';
    }

    return 0;
}