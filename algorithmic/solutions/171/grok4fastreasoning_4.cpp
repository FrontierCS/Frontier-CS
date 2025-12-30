#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    vector<pair<int, int>> points(M);
    for (int k = 0; k < M; k++) {
        cin >> points[k].first >> points[k].second;
    }
    vector<string> seq;
    int ci = points[0].first;
    int cj = points[0].second;
    for (int k = 1; k < M; k++) {
        int ti = points[k].first;
        int tj = points[k].second;
        int di = ti - ci;
        int dj = tj - cj;

        // Horizontal: from cj to tj
        int ch_direct = abs(tj - cj);
        int ch_left = 1 + tj;
        int ch_right = 1 + abs((N - 1) - tj);
        int min_h = min({ch_direct, ch_left, ch_right});
        string type_h = "direct";
        if (ch_direct == min_h) {
            type_h = "direct";
        } else if (ch_left == min_h) {
            type_h = "left";
        } else {
            type_h = "right";
        }

        // Vertical: from ci to ti
        int cv_direct = abs(ti - ci);
        int cv_up = 1 + ti;
        int cv_down = 1 + abs((N - 1) - ti);
        int min_v = min({cv_direct, cv_up, cv_down});
        string type_v = "direct";
        if (cv_direct == min_v) {
            type_v = "direct";
        } else if (cv_up == min_v) {
            type_v = "up";
        } else {
            type_v = "down";
        }

        // Generate sequence: horiz first, then vert
        // Horiz actions
        if (type_h == "direct") {
            if (tj > cj) {
                for (int s = 0; s < tj - cj; s++) seq.push_back("M R");
            } else if (tj < cj) {
                for (int s = 0; s < cj - tj; s++) seq.push_back("M L");
            }
        } else if (type_h == "left") {
            seq.push_back("S L");
            for (int s = 0; s < tj; s++) seq.push_back("M R");
        } else { // right
            seq.push_back("S R");
            if (tj < N - 1) {
                for (int s = 0; s < (N - 1 - tj); s++) seq.push_back("M L");
            }
        }

        // Vert actions (now at row ci, col tj)
        if (type_v == "direct") {
            if (ti > ci) {
                for (int s = 0; s < ti - ci; s++) seq.push_back("M D");
            } else if (ti < ci) {
                for (int s = 0; s < ci - ti; s++) seq.push_back("M U");
            }
        } else if (type_v == "up") {
            seq.push_back("S U");
            for (int s = 0; s < ti; s++) seq.push_back("M D");
        } else { // down
            seq.push_back("S D");
            if (ti < N - 1) {
                for (int s = 0; s < (N - 1 - ti); s++) seq.push_back("M U");
            }
        }

        // Update position
        ci = ti;
        cj = tj;
    }
    for (auto& s : seq) {
        cout << s << endl;
    }
    return 0;
}