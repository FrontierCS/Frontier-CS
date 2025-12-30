#include <iostream>
#include <vector>
#include <queue>
#include <cmath>
#include <algorithm>
#include <string>
#include <cstdio>

using namespace std;

const int N = 30;
double h_est[N][N-1]; // horizontal edges: (i,j) -> (i,j+1)
double v_est[N-1][N]; // vertical edges: (i,j) -> (i+1,j)
int h_cnt[N][N-1] = {0};
int v_cnt[N-1][N] = {0};

// Parameters
const double C = 2000.0; // exploration constant
double learning_rate = 0.5;
const double decay = 0.998;

struct Node {
    int i, j;
    double dist;
    Node(int i, int j, double d) : i(i), j(j), dist(d) {}
    bool operator>(const Node& other) const {
        return dist > other.dist;
    }
};

int main() {
    // Initialize estimates to 5000
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N-1; ++j)
            h_est[i][j] = 5000.0;
    for (int i = 0; i < N-1; ++i)
        for (int j = 0; j < N; ++j)
            v_est[i][j] = 5000.0;

    for (int k = 1; k <= 1000; ++k) {
        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;

        double log_factor = sqrt(log(k + 10));

        // Dijkstra with optimistic weights (lower confidence bound)
        vector<vector<double>> dist(N, vector<double>(N, 1e18));
        vector<vector<pair<int,int>>> prev(N, vector<pair<int,int>>(N, {-1,-1}));
        vector<vector<char>> move_from(N, vector<char>(N, ' '));
        priority_queue<Node, vector<Node>, greater<Node>> pq;

        dist[si][sj] = 0.0;
        pq.push(Node(si, sj, 0.0));

        while (!pq.empty()) {
            Node cur = pq.top(); pq.pop();
            int i = cur.i, j = cur.j;
            if (abs(dist[i][j] - cur.dist) > 1e-9) continue;
            if (i == ti && j == tj) break;

            // Up
            if (i > 0) {
                double bonus = C * log_factor / sqrt(v_cnt[i-1][j] + 1);
                double w = max(1.0, v_est[i-1][j] - bonus);
                if (dist[i-1][j] > dist[i][j] + w) {
                    dist[i-1][j] = dist[i][j] + w;
                    prev[i-1][j] = {i, j};
                    move_from[i-1][j] = 'U';
                    pq.push(Node(i-1, j, dist[i-1][j]));
                }
            }
            // Down
            if (i < N-1) {
                double bonus = C * log_factor / sqrt(v_cnt[i][j] + 1);
                double w = max(1.0, v_est[i][j] - bonus);
                if (dist[i+1][j] > dist[i][j] + w) {
                    dist[i+1][j] = dist[i][j] + w;
                    prev[i+1][j] = {i, j};
                    move_from[i+1][j] = 'D';
                    pq.push(Node(i+1, j, dist[i+1][j]));
                }
            }
            // Left
            if (j > 0) {
                double bonus = C * log_factor / sqrt(h_cnt[i][j-1] + 1);
                double w = max(1.0, h_est[i][j-1] - bonus);
                if (dist[i][j-1] > dist[i][j] + w) {
                    dist[i][j-1] = dist[i][j] + w;
                    prev[i][j-1] = {i, j};
                    move_from[i][j-1] = 'L';
                    pq.push(Node(i, j-1, dist[i][j-1]));
                }
            }
            // Right
            if (j < N-1) {
                double bonus = C * log_factor / sqrt(h_cnt[i][j] + 1);
                double w = max(1.0, h_est[i][j] - bonus);
                if (dist[i][j+1] > dist[i][j] + w) {
                    dist[i][j+1] = dist[i][j] + w;
                    prev[i][j+1] = {i, j};
                    move_from[i][j+1] = 'R';
                    pq.push(Node(i, j+1, dist[i][j+1]));
                }
            }
        }

        // Reconstruct path
        string path = "";
        int i = ti, j = tj;
        while (!(i == si && j == sj)) {
            char m = move_from[i][j];
            path += m;
            int pi = prev[i][j].first, pj = prev[i][j].second;
            i = pi; j = pj;
        }
        reverse(path.begin(), path.end());

        // Output path
        cout << path << endl;
        cout.flush();

        // Read observed length
        int L_obs;
        cin >> L_obs;

        // Compute sum of current estimates along the path
        double S = 0.0;
        vector<pair<char, pair<int,int>>> edges; // type, coordinates
        i = si; j = sj;
        for (char m : path) {
            if (m == 'U') {
                S += v_est[i-1][j];
                edges.push_back({'v', {i-1, j}});
                i--;
            } else if (m == 'D') {
                S += v_est[i][j];
                edges.push_back({'v', {i, j}});
                i++;
            } else if (m == 'L') {
                S += h_est[i][j-1];
                edges.push_back({'h', {i, j-1}});
                j--;
            } else if (m == 'R') {
                S += h_est[i][j];
                edges.push_back({'h', {i, j}});
                j++;
            }
        }

        double error = L_obs - S;
        int len = edges.size();
        if (len > 0) {
            double update = learning_rate * error / len;
            for (auto& e : edges) {
                char type = e.first;
                int x = e.second.first, y = e.second.second;
                if (type == 'h') {
                    h_cnt[x][y]++;
                    h_est[x][y] += update;
                    // Clip to plausible range
                    if (h_est[x][y] < 1000) h_est[x][y] = 1000;
                    if (h_est[x][y] > 9000) h_est[x][y] = 9000;
                } else {
                    v_cnt[x][y]++;
                    v_est[x][y] += update;
                    if (v_est[x][y] < 1000) v_est[x][y] = 1000;
                    if (v_est[x][y] > 9000) v_est[x][y] = 9000;
                }
            }
        }

        // Decay learning rate
        learning_rate *= decay;
    }

    return 0;
}