"""Tests for LaTeX post-processing."""
from researchsensei.canonical.latex_postprocessor import postprocess_latex


class TestLatexPostProcessor:
    def test_fixes_mathbf_letter_spacing(self):
        input_latex = r"\mathbf {E L B O} = \mathbb {E} [ \log p (x | z) ]"
        result = postprocess_latex(input_latex)
        assert r"\mathbf{ELBO}" in result
        assert "E L B O" not in result

    def test_fixes_text_letter_spacing(self):
        input_latex = r"\text { Precision } = \frac {T P}{T P + F P}"
        result = postprocess_latex(input_latex)
        assert r"\text{Precision}" in result
        assert "P r e c i s i o n" not in result

    def test_fixes_mathrm_letter_spacing(self):
        input_latex = r"\mathrm {o f f s e t}"
        result = postprocess_latex(input_latex)
        assert r"\mathrm{offset}" in result

    def test_fixes_command_space_brace(self):
        input_latex = r"\mathcal {L} = \mathbb {E} [ x ]"
        result = postprocess_latex(input_latex)
        assert r"\mathcal{" in result
        assert r"\mathcal {" not in result
        assert r"\mathbb{" in result

    def test_fixes_subscript_spacing(self):
        input_latex = r"x _ {0} + y ^ {2}"
        result = postprocess_latex(input_latex)
        assert "_{0}" in result
        assert "^{2}" in result

    def test_preserves_correct_latex(self):
        input_latex = r"\mathcal{L}_{\mathcal{DM}} = \mathbb{E}_{t,x_0,\epsilon}[||\epsilon - \epsilon_\theta(...)||^2]"
        result = postprocess_latex(input_latex)
        assert result == input_latex

    def test_fixes_multiple_command_space_braces(self):
        input_latex = r"\mathcal {L} _ {\mathcal {F}} + \mathcal {L} _ {\mathcal {P I}}"
        result = postprocess_latex(input_latex)
        assert r"\mathcal{" in result
        assert r"\mathcal {" not in result

    def test_empty_input(self):
        assert postprocess_latex("") == ""
        assert postprocess_latex("   ") == "   "

    def test_collapses_double_spaces(self):
        input_latex = r"A  =  B"
        result = postprocess_latex(input_latex)
        assert "  " not in result

    def test_does_not_fix_semantic_errors(self):
        input_latex = r"p _ {0} (x _ {0})"
        result = postprocess_latex(input_latex)
        assert "_{0}" in result

    def test_fixes_complex_formula(self):
        input_latex = (
            r"\mathcal {L} _ {\mathcal {D M}} = \mathbb {E} _ {t, x _ {0}, \epsilon} "
            r"\left[ | | \epsilon - \epsilon_ {\theta} "
            r"(\sqrt {\overline {\alpha} _ {t}} x _ {0} + \sqrt {1 - \overline {\alpha} _ {t}} \epsilon , t) | | ^ {2} \right]"
        )
        result = postprocess_latex(input_latex)
        assert r"\mathcal{" in result
        assert r"\mathbb{" in result

    def test_fixes_subscript_in_product(self):
        input_latex = r"\prod_ {t = 1} ^ {T}"
        result = postprocess_latex(input_latex)
        assert "_{t=1}" in result
        assert "^{T}" in result

    def test_fixes_ddmt_formula_003_spacing(self):
        input_latex = (
            r"p _ {0} \left(x _ {0}, \dots , x _ {t - 1} \mid x _ {T}\right) = "
            r"p \left(x _ {T}\right) \prod_ {t = 1} ^ {T} "
            r"p _ {0} \left(x _ {t - 1} \mid x _ {t}\right)"
        )
        result = postprocess_latex(input_latex)
        assert "_{0}" in result
        assert "_{t-1}" in result or "_{t - 1}" not in result
        assert "_{T}" in result
        assert "_{t=1}" in result
