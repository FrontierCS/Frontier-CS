#include <bits/stdc++.h>
using namespace std;

const int MAXR = 100;
const int MAXC = 100;
const int MAX_POSES = MAXR * MAXC * 4; // max poses
const int MAX_STEPS = 100000;

int r, c;
vector<string> grid;
int dist[MAXR][MAXC][4]; // distance to wall for each cell and direction
int di[4] = {-1, 0, 1, 0};
int dj[4] = {0, 1, 0, -1};

// Precomputed data for each pose (indexed by (i*c + j)*4 + dir)
vector<int> pose_i, pose_j, pose_dir, pose_dist;
vector<int> left_idx, right_idx, step_idx;

inline int get_idx(int i, int j, int d) {
    return (i * c + j) * 4 + d;
}

void precompute() {
    int total = r * c * 4;
    pose_i.resize(total);
    pose_j.resize(total);
    pose_dir.resize(total);
    pose_dist.resize(total);
    left_idx.resize(total);
    right_idx.resize(total);
    step_idx.resize(total, -1);

    // Precompute dist for each open cell and each direction
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] != '.') continue;
            for (int d = 0; d < 4; ++d) {
                int cnt = 0;
                int ni = i + di[d];
                int nj = j + dj[d];
                while (ni >= 0 && ni < r && nj >= 0 && nj < c && grid[ni][nj] == '.') {
                    ++cnt;
                    ni += di[d];
                    nj += dj[d];
                }
                dist[i][j][d] = cnt;
            }
        }
    }

    // Fill pose arrays and transitions
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            for (int d = 0; d < 4; ++d) {
                int idx = get_idx(i, j, d);
                pose_i[idx] = i;
                pose_j[idx] = j;
                pose_dir[idx] = d;
                pose_dist[idx] = dist[i][j][d];

                left_idx[idx] = get_idx(i, j, (d + 3) % 4);
                right_idx[idx] = get_idx(i, j, (d + 1) % 4);

                int ni = i + di[d];
                int nj = j + dj[d];
                if (ni >= 0 && ni < r && nj >= 0 && nj < c && grid[ni][nj] == '.') {
                    step_idx[idx] = get_idx(ni, nj, d);
                }
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> r >> c;
    grid.resize(r);
    for (int i = 0; i < r; ++i) {
        cin >> grid[i];
    }

    precompute();

    // Initial belief set: all open cells with all directions
    vector<int> B;
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < 4; ++d) {
                    B.push_back(get_idx(i, j, d));
                }
            }
        }
    }

    // First observation
    int d;
    cin >> d;
    if (d == -1) return 0;

    // Filter by first observation
    vector<int> B_new;
    for (int idx : B) {
        if (pose_dist[idx] == d) {
            B_new.push_back(idx);
        }
    }
    B.swap(B_new);

    int steps = 0;
    while (steps < MAX_STEPS) {
        ++steps;

        // Check if unique
        if (B.size() == 1) {
            int idx = B[0];
            cout << "yes " << pose_i[idx]+1 << " " << pose_j[idx]+1 << endl;
            break;
        }

        // Determine if step is safe for all poses in B
        bool step_allowed = true;
        for (int idx : B) {
            if (step_idx[idx] == -1) {
                step_allowed = false;
                break;
            }
        }

        // Evaluate left action
        int left_cnt[100] = {0};
        for (int idx : B) {
            int nidx = left_idx[idx];
            int pred_d = pose_dist[nidx];
            ++left_cnt[pred_d];
        }
        int worst_left = *max_element(left_cnt, left_cnt + 100);

        // Evaluate right action
        int right_cnt[100] = {0};
        for (int idx : B) {
            int nidx = right_idx[idx];
            int pred_d = pose_dist[nidx];
            ++right_cnt[pred_d];
        }
        int worst_right = *max_element(right_cnt, right_cnt + 100);

        int worst_step = INT_MAX;
        if (step_allowed) {
            int step_cnt[100] = {0};
            for (int idx : B) {
                int nidx = step_idx[idx];
                int pred_d = pose_dist[nidx];
                ++step_cnt[pred_d];
            }
            worst_step = *max_element(step_cnt, step_cnt + 100);
        }

        // Choose action with smallest worst-case size
        int action; // 0 left, 1 right, 2 step
        if (worst_left <= worst_right && worst_left <= worst_step) {
            action = 0;
        } else if (worst_right <= worst_step) {
            action = 1;
        } else {
            action = 2;
        }

        // Output action
        if (action == 0) {
            cout << "left" << endl;
        } else if (action == 1) {
            cout << "right" << endl;
        } else {
            cout << "step" << endl;
        }

        // Apply action to belief set
        vector<int> B_next;
        if (action == 0) {
            for (int idx : B) B_next.push_back(left_idx[idx]);
        } else if (action == 1) {
            for (int idx : B) B_next.push_back(right_idx[idx]);
        } else {
            for (int idx : B) B_next.push_back(step_idx[idx]);
        }

        // Read next observation
        cin >> d;
        if (d == -1) break;

        // Filter by observation
        vector<int> B_filtered;
        for (int idx : B_next) {
            if (pose_dist[idx] == d) {
                B_filtered.push_back(idx);
            }
        }
        B.swap(B_filtered);

        if (B.empty()) {
            // Inconsistent observation – shouldn't happen, but fallback
            cout << "no" << endl;
            break;
        }
    }

    if (steps >= MAX_STEPS) {
        cout << "no" << endl;
    }

    return 0;
}