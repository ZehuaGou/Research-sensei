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

    def test_fixes_space_before_subscript_operator(self):
        input_latex = r"\lambda _{1} + \mathcal{L} _{\mathrm{aux}}"
        result = postprocess_latex(input_latex)
        assert r"\lambda_{1}" in result
        assert r"\mathcal{L}_{\mathrm{aux}}" in result

    def test_fixes_space_after_subscript_operator_with_nested_content(self):
        input_latex = r"\mathbb{R}^ {d_{i}} + \sum_{j=0}^ {l_{w} - 1}"
        result = postprocess_latex(input_latex)
        assert r"\mathbb{R}^{d_{i}}" in result
        assert r"\sum_{j=0}^{l_{w} - 1}" in result

    def test_preserves_relation_spacing_inside_subscripts(self):
        input_latex = r"\max _ {j \in N (i)} x_j"
        result = postprocess_latex(input_latex)
        assert r"\max_{j \in N(i)}" in result
        assert r"\inN" not in result

    def test_fixes_known_ocr_split_formula_tokens(self):
        input_latex = (
            r"t 2 v(x) = \left\{a, & i f & x=0 \\ b, & f o r & x>0\right. "
            r"+ R e L U \left(y\right) + w h e r e + T r + E r_{t}^{i} + F c_{1}"
        )
        result = postprocess_latex(input_latex)
        assert "t2v" in result
        assert "if" in result
        assert "for" in result
        assert "ReLU" in result
        assert "where" in result
        assert "Tr" in result
        assert r"Er_{t}^{i}" in result
        assert r"Fc_{1}" in result

    def test_fixes_rolling_error_sensor_superscript_ocr(self):
        input_latex = (
            r"\mu_ {t} ^ {i} = \frac {1}{l _ {w}} \sum_ {j = 0} ^ {l _ {w} - 1} "
            r"E r _ {t - j} ^ {j} \tag {9}"
        )
        result = postprocess_latex(input_latex)
        assert r"Er_{t-j}^{i}" in result
        assert r"Er_{t-j}^{j}" not in result

    def test_fixes_rolling_variance_sensor_superscript_ocr(self):
        input_latex = (
            r"\left(\sigma_ {t} ^ {i}\right) ^ {2} = \frac {1}{l _ {w} - 1} "
            r"\sum_ {j = 0} ^ {l _ {w} - 1} \left(E r _ {t - j} ^ {j} - \mu_ {t} ^ {j}\right) ^ {2}."
        )
        result = postprocess_latex(input_latex)
        assert r"Er_{t-j}^{i}" in result
        assert r"\mu_{t}^{i}" in result
        assert r"Er_{t-j}^{j}" not in result
        assert r"\mu_{t}^{j}" not in result

    def test_strips_inline_math_wrappers_from_formula_blocks(self):
        input_latex = r"$A_{t} = \sum_{i=1}^{N} a_{t}^{i}$. \tag{11}"
        result = postprocess_latex(input_latex)
        assert result == r"A_{t} = \sum_{i=1}^{N} a_{t}^{i} \tag{11}"

    def test_fixes_overescaped_norm_delimiters(self):
        input_latex = r"$L = \\|\hat{x}_t - x_t\\|^2$. \tag{7}"
        result = postprocess_latex(input_latex)
        assert result == r"L = \|\hat{x}_t - x_t\|^2 \tag{7}"

    def test_fixes_nested_command_subscript_spacing(self):
        input_latex = r"\mathbf{Y} _ { \mathrm{sta} } ^ {S}"
        result = postprocess_latex(input_latex)
        assert result == r"\mathbf{Y}_{\mathrm{sta}}^{S}"

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

    def test_normalizes_circled_underbrace_label(self):
        input_latex = r"\underbrace{x+y}_{②}"
        result = postprocess_latex(input_latex)
        assert result == r"\underbrace{x+y}_{\text{(2)}}"

    def test_normalizes_component_label_sequence(self):
        input_latex = r"\mathcal{L}_{\mathrm{AVAE}} = ① + Ⓐ - ⓙ - ⓙ \tag{8}"
        result = postprocess_latex(input_latex)
        assert r"\text{(1)} + \text{(A)} - \text{(i)} - \text{(ii)}" in result
        assert "①" not in result
        assert "ⓙ" not in result
