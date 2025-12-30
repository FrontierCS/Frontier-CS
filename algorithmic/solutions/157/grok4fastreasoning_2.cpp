#include <bits/stdc++.h>
using namespace std;

int get_dx(char dir) {
    if (dir == 'U') return -1;
    if (dir == 'D') return 1;
    return 0;
}

int get_dy(char dir) {
    if (dir == 'L') return -1;
    if (dir == 'R') return 1;
    return 0;
}

char get_opp(char dir) {
    if (dir == 'U') return 'D';
    if (dir == 'D') return 'U';
    if (dir == 'L') return 'R';
    if (dir == 'R') return 'L';
    assert(false);
    return ' ';
}

int get_matched_edges(int bd[11][11], int n, pair<int, int> emp) {
    int ex = emp.first, ey = emp.second;
    int edges = 0;
    // horizontal
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n - 1; j++) {
            bool pos1_valid = (i != ex || j != ey);
            bool pos2_valid = (i != ex || j + 1 != ey);
            if (pos1_valid && pos2_valid) {
                int m1 = bd[i][j];
                int m2 = bd[i][j + 1];
                if ((m1 & 4) && (m2 & 1)) edges++;
            }
        }
    }
    // vertical
    for (int j = 0; j < n; j++) {
        for (int i = 0; i < n - 1; i++) {
            bool pos1_valid = (i != ex || j != ey);
            bool pos2_valid = (i + 1 != ex || j != ey);
            if (pos1_valid && pos2_valid) {
                int m1 = bd[i][j];
                int m2 = bd[i + 1][j];
                if ((m1 & 8) && (m2 & 2)) edges++;
            }
        }
    }
    return edges;
}

int main() {
    int N, T;
    cin >> N >> T;
    vector<string> input(N);
    for (int i = 0; i < N; i++) {
        cin >> input[i];
    }
    int cur_bd[11][11] = {0};
    pair<int, int> emp;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            char c = input[i][j];
            int val;
            if (c >= '0' && c <= '9') val = c - '0';
            else val = 10 + (c - 'a');
            cur_bd[i][j] = val;
            if (val == 0) {
                emp = {i, j};
            }
        }
    }
    int current_bd[11][11];
    memcpy(current_bd, cur_bd, sizeof(cur_bd));
    pair<int, int> current_emp = emp;
    string seq = "";
    const int max_edges = N * N - 2;
    while (seq.size() < (size_t)T) {
        int current_edges = get_matched_edges(current_bd, N, current_emp);
        if (current_edges == max_edges) break;
        int best_la = -1;
        char best_first = 0;
        int best_first_score = -1;
        string dirs = "UDLR";
        for (char first : dirs) {
            int fdx = get_dx(first), fdy = get_dy(first);
            int ftx = current_emp.first + fdx, fty = current_emp.second + fdy;
            if (ftx < 0 || ftx >= N || fty < 0 || fty >= N) continue;
            int temp1[11][11];
            memcpy(temp1, current_bd, sizeof(current_bd));
            swap(temp1[current_emp.first][current_emp.second], temp1[ftx][fty]);
            pair<int, int> emp1 = {ftx, fty};
            int score1 = get_matched_edges(temp1, N, emp1);
            int la_max = score1;
            char op = get_opp(first);
            for (char second : dirs) {
                if (second == op) continue;
                int sdx = get_dx(second), sdy = get_dy(second);
                int stx = emp1.first + sdx, sty = emp1.second + sdy;
                if (stx < 0 || stx >= N || sty < 0 || sty >= N) continue;
                int temp2[11][11];
                memcpy(temp2, temp1, sizeof(temp1));
                swap(temp2[emp1.first][emp1.second], temp2[stx][sty]);
                pair<int, int> emp2 = {stx, sty};
                int score2 = get_matched_edges(temp2, N, emp2);
                la_max = max(la_max, score2);
            }
            bool better = (la_max > best_la) || (la_max == best_la && score1 > best_first_score);
            if (better) {
                best_la = la_max;
                best_first = first;
                best_first_score = score1;
            }
        }
        if (best_first == 0 || best_la <= current_edges) break;
        // apply
        int fdx = get_dx(best_first), fdy = get_dy(best_first);
        int ftx = current_emp.first + fdx, fty = current_emp.second + fdy;
        swap(current_bd[current_emp.first][current_emp.second], current_bd[ftx][fty]);
        current_emp = {ftx, fty};
        seq += best_first;
    }
    cout << seq << endl;
    return 0;
}