#include <bits/stdc++.h>
using namespace std;

static inline string trim_copy(string s) {
    size_t i = 0;
    while (i < s.size() && isspace((unsigned char)s[i])) i++;
    size_t j = s.size();
    while (j > i && isspace((unsigned char)s[j - 1])) j--;
    return s.substr(i, j - i);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;
    string dummy;
    getline(cin, dummy); // consume rest of line

    uint64_t rng = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    auto rnd64 = [&]() -> uint64_t {
        rng ^= rng << 7;
        rng ^= rng >> 9;
        rng ^= rng << 8;
        return rng;
    };

    int seenCenters = 0;
    int sinceNew = 0;
    int moves = 0;

    while (true) {
        string line;
        if (!getline(cin, line)) return 0;
        line = trim_copy(line);
        if (line.empty()) continue;

        // Parse first token only (robust to possible extra tokens).
        string token;
        {
            stringstream ss(line);
            ss >> token;
        }

        if (token == "treasure") break;

        bool isCenter = (token == "center");
        if (isCenter) {
            seenCenters++;
            sinceNew = 0;
        } else {
            sinceNew++;
        }

        // Strategy:
        // - Mostly follow local rotor (take passage 0, advance marker by +1).
        // - Occasionally take a random passage to improve mixing.
        // - More randomness early and while new chambers still appear frequently.
        bool exploreMode = (sinceNew < 2000); // likely still discovering
        int jumpProb = exploreMode ? 3 : 1;   // out of 10

        int e;
        if ((int)(rnd64() % 10) < jumpProb) e = (int)(rnd64() % m);
        else e = 0;

        int setOffset = (e + 1) % m;
        cout << setOffset << " left " << e << "\n" << flush;

        moves++;
        if (moves >= 50000) {
            // Should never happen if judge is correct; avoid extra output.
            return 0;
        }
    }

    return 0;
}