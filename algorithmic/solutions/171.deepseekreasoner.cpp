#include <iostream>
#include <vector>
#include <string>

int main() {
    int N, M;
    std::cin >> N >> M;
    std::vector<std::pair<int, int>> pts(M);
    for (int i = 0; i < M; ++i) {
        std::cin >> pts[i].first >> pts[i].second;
    }
    int r = pts[0].first, c = pts[0].second;
    std::vector<std::string> actions;
    for (int idx = 1; idx < M; ++idx) {
        int tr = pts[idx].first, tc = pts[idx].second;
        // vertical movement
        int dr = tr - r;
        if (dr > 0) {
            int direct = dr;
            int slide = 1 + (N - 1 - tr);
            if (direct <= slide) {
                for (int i = 0; i < dr; ++i) actions.push_back("M D");
            } else {
                actions.push_back("S D");
                for (int i = 0; i < N - 1 - tr; ++i) actions.push_back("M U");
            }
        } else if (dr < 0) {
            int dr_abs = -dr;
            int direct = dr_abs;
            int slide = 1 + tr;
            if (direct <= slide) {
                for (int i = 0; i < dr_abs; ++i) actions.push_back("M U");
            } else {
                actions.push_back("S U");
                for (int i = 0; i < tr; ++i) actions.push_back("M D");
            }
        }
        r = tr;
        // horizontal movement
        int dc = tc - c;
        if (dc > 0) {
            int direct = dc;
            int slide = 1 + (N - 1 - tc);
            if (direct <= slide) {
                for (int i = 0; i < dc; ++i) actions.push_back("M R");
            } else {
                actions.push_back("S R");
                for (int i = 0; i < N - 1 - tc; ++i) actions.push_back("M L");
            }
        } else if (dc < 0) {
            int dc_abs = -dc;
            int direct = dc_abs;
            int slide = 1 + tc;
            if (direct <= slide) {
                for (int i = 0; i < dc_abs; ++i) actions.push_back("M L");
            } else {
                actions.push_back("S L");
                for (int i = 0; i < tc; ++i) actions.push_back("M R");
            }
        }
        c = tc;
    }
    for (const std::string& s : actions) {
        std::cout << s << "\n";
    }
    return 0;
}