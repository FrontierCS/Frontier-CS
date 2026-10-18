#include <cmath>
#include <algorithm>

// Natural-log calibration above the previous 60-point threshold.
// Keep validation and low scores; an exact zero minimization cost earns 100.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0 || !(value > 0.0L) || !(anchor > 0.0L))
        return old_points;
    const long double delta = minimize ? std::log(anchor) - std::log(value)
                                       : std::log(value) - std::log(anchor);
    return (double)std::min(100.0L, 60.0L + delta);
}

#include "testlib.h"

static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

#include <bits/stdc++.h>
using namespace std;

const int maxn = 35;

int n, m;
int sr, sc, er, ec;
int vis[maxn][maxn];
string op, s[maxn];

inline bool isPalin(string str) {
	for (int i = 0; i < str.size(); ++i)
		if (str[i] != str[str.size() - 1 - i]) return false;
	return true;
}

inline void dfs(int x, int y) {
	if (vis[x][y]) return;
	vis[x][y] = 1;
	if (x - 1 >= 0 && s[x - 1][y] != '0') dfs(x - 1, y);
	if (x + 1 < n && s[x + 1][y] != '0') dfs(x + 1, y);
	if (y - 1 >= 0 && s[x][y - 1] != '0') dfs(x, y - 1);
	if (y + 1 < m && s[x][y + 1] != '0') dfs(x, y + 1);
}

int main(int argc, char **argv){
	registerTestlibCmd(argc, argv);
	n = inf.readInt(), m = inf.readInt();
	inf.readString();
	for (int i = 0; i < n; ++i)
		s[i] = inf.readString();
	sr = inf.readInt(), sc = inf.readInt(), er = inf.readInt(), ec = inf.readInt();
	--sr, --sc, --er, --ec;
	op = ouf.readString();

	if (op == "-1") {
		dfs(sr, sc);
		for (int i = 0; i < n; ++i) for (int j = 0; j < m; ++j)
			if (s[i][j] == '1' && !vis[i][j])
				quitf(_ok, "Correct.");
		quitp(0.0, "Answer exists but -1 found.");
	}

	if (!isPalin(op)) {
		quitp(0.0, "Not palindrome.");
	}
	else {
		vis[sr][sc] = 1;
		for (auto c: op) {
			int nr = sr, nc = sc;
			if (c == 'L' && nc - 1 >= 0 && s[nr][nc - 1] != '0') --nc;
			else if (c == 'R' && nc + 1 < m && s[nr][nc + 1] != '0') ++nc;
			else if (c == 'U' && nr - 1 >= 0 && s[nr - 1][nc] != '0') --nr;
			else if (c == 'D' && nr + 1 < n && s[nr + 1][nc] != '0') ++nr;
			sr = nr, sc = nc;
			vis[sr][sc] = 1;
		}
		if (sr != er || sc != ec) {
			quitp(0.0, "Not ending at (er, ec)");
		}
		int blank = 0;
		for (int i = 0; i < n; ++i) for (int j = 0; j < m; ++j) {
			blank += (s[i][j] == '1');
			if (s[i][j] == '1' && !vis[i][j]) {
				quitp(0.0, "Blank cells unvisited");
			}
		}
		int bound = 12 * blank * max(n, m);
		double r = max(0.0, 2.0 - (double)op.size() / bound);
		double pnt = referenceScore(r), unbounded_pnt = pnt;
    pnt = natural_log_score(100.0 * pnt, op.size(), bound, true) / 100.0;
		unbounded_pnt = pnt;
		char mes[128];
		sprintf(mes, "Ratio: %.12lf, RatioUnbounded: %.12lf", pnt, unbounded_pnt);
		quitp(pnt, "%s", mes);
	}
	return 0;
}
