#include <bits/stdc++.h>
using namespace std;

const int N = 20;
int M;
vector<string> s;
char mat[N][N];

// check if a string is a subsequence of current matrix
bool is_subsequence(const string& str) {
    int len = str.size();
    // horizontal
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            bool ok = true;
            for (int p = 0; p < len; ++p) {
                if (mat[i][(j+p)%N] != str[p]) {
                    ok = false;
                    break;
                }
            }
            if (ok) return true;
        }
    }
    // vertical
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            bool ok = true;
            for (int p = 0; p < len; ++p) {
                if (mat[(i+p)%N][j] != str[p]) {
                    ok = false;
                    break;
                }
            }
            if (ok) return true;
        }
    }
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> M;
    s.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> s[i];
    }

    // random initialization
    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<> dis(0, 7);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            mat[i][j] = 'A' + dis(gen);
        }
    }

    const int ITER = 30;
    for (int iter = 0; iter < ITER; ++iter) {
        int votes[N][N][8] = {0};

        for (const string& str : s) {
            int len = str.size();
            int best_score = -1e9;
            int best_ori = -1, best_i = -1, best_j = -1;

            // horizontal placements
            for (int i = 0; i < N; ++i) {
                for (int j = 0; j < N; ++j) {
                    int score = 0;
                    for (int p = 0; p < len; ++p) {
                        char c = mat[i][(j+p)%N];
                        if (c == str[p]) score++;
                        else score--;
                    }
                    if (score > best_score) {
                        best_score = score;
                        best_ori = 0;
                        best_i = i;
                        best_j = j;
                    }
                }
            }

            // vertical placements
            for (int i = 0; i < N; ++i) {
                for (int j = 0; j < N; ++j) {
                    int score = 0;
                    for (int p = 0; p < len; ++p) {
                        char c = mat[(i+p)%N][j];
                        if (c == str[p]) score++;
                        else score--;
                    }
                    if (score > best_score) {
                        best_score = score;
                        best_ori = 1;
                        best_i = i;
                        best_j = j;
                    }
                }
            }

            // add votes from the best placement
            if (best_ori == 0) { // horizontal
                for (int p = 0; p < len; ++p) {
                    int ci = best_i;
                    int cj = (best_j + p) % N;
                    votes[ci][cj][str[p]-'A']++;
                }
            } else { // vertical
                for (int p = 0; p < len; ++p) {
                    int ci = (best_i + p) % N;
                    int cj = best_j;
                    votes[ci][cj][str[p]-'A']++;
                }
            }
        }

        // update matrix
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                int max_vote = -1;
                int best_c = 0;
                for (int c = 0; c < 8; ++c) {
                    if (votes[i][j][c] > max_vote) {
                        max_vote = votes[i][j][c];
                        best_c = c;
                    }
                }
                if (max_vote > 0) {
                    mat[i][j] = 'A' + best_c;
                }
                // else keep current value
            }
        }
    }

    // output
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cout << mat[i][j];
        }
        cout << '\n';
    }

    return 0;
}